from __future__ import annotations

import asyncio
import builtins
import contextlib
import datetime
import typing as t

from audex import utils
from audex.entity.segment import Segment
from audex.entity.session import Session
from audex.entity.utterance import Utterance
from audex.exceptions import NoActiveSessionError
from audex.filters.generated import segment_filter
from audex.filters.generated import session_filter
from audex.filters.generated import utterance_filter
from audex.filters.generated import vp_filter
from audex.helper.mixin import LoggingMixin
from audex.helper.stream import AsyncStream
from audex.lib.cache import KVCache
from audex.lib.recorder import AudioFormat
from audex.lib.recorder import AudioRecorder
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.segment import SegmentRepository
from audex.lib.repos.session import SessionRepository
from audex.lib.repos.utterance import UtteranceRepository
from audex.lib.repos.vp import VPRepository
from audex.lib.session import SessionManager
from audex.lib.transcription import Transcription
from audex.lib.transcription import TranscriptionError
from audex.lib.transcription import events
from audex.lib.vpr import VPR
from audex.lib.vpr import VPRError
from audex.service import BaseService
from audex.service.decorators import require_auth
from audex.service.session.const import ErrorMessages
from audex.service.session.exceptions import InternalSessionServiceError
from audex.service.session.exceptions import RecordingError
from audex.service.session.exceptions import SessionNotFoundError
from audex.service.session.exceptions import SessionServiceError
from audex.service.session.types import CreateSessionCommand
from audex.service.session.types import Delta
from audex.service.session.types import Done
from audex.service.session.types import Start
from audex.types import AbstractSession
from audex.valueobj.utterance import Speaker


class SessionServiceConfig(t.NamedTuple):
    """SessionService configuration."""

    audio_key_prefix: str = "audio"
    segment_buffer_ms: int = 1000
    sr: int = 16000
    vpr_sr: int = 16000
    vpr_threshold: float = 0.6


class SessionService(BaseService):
    """Service for managing recording sessions."""

    __logtag__ = "audex.service.session"

    def __init__(
        self,
        session_manager: SessionManager,
        cache: KVCache,
        config: SessionServiceConfig,
        doctor_repo: DoctorRepository,
        session_repo: SessionRepository,
        segment_repo: SegmentRepository,
        utterance_repo: UtteranceRepository,
        vp_repo: VPRepository,
        vpr: VPR,
        transcription: Transcription,
        recorder: AudioRecorder,
    ):
        super().__init__(session_manager=session_manager, cache=cache, doctor_repo=doctor_repo)
        self.config = config
        self.session_repo = session_repo
        self.segment_repo = segment_repo
        self.utterance_repo = utterance_repo
        self.vp_repo = vp_repo
        self.vpr = vpr
        self.transcription = transcription
        self.recorder = recorder

    @require_auth
    async def create(self, command: CreateSessionCommand) -> Session:
        """Create a new recording session."""
        try:
            session = Session(
                doctor_id=command.doctor_id,
                patient_name=command.patient_name,
                clinic_number=command.clinic_number,
                medical_record_number=command.medical_record_number,
                diagnosis=command.diagnosis,
                notes=command.notes,
            )

            uid = await self.session_repo.create(session)
            session = await self.session_repo.read(uid)

            if session is None:
                raise SessionServiceError(ErrorMessages.SESSION_CREATE_FAILED)

            self.logger.info(f"Created session {uid} for doctor {command.doctor_id}")
            return session

        except SessionServiceError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            raise InternalSessionServiceError(ErrorMessages.SESSION_CREATE_FAILED) from e

    @require_auth
    async def get(self, session_id: str) -> Session | None:
        """Get session by ID."""
        try:
            return await self.session_repo.read(session_id)
        except Exception as e:
            self.logger.error(f"Failed to get session {session_id}: {e}")
            raise InternalSessionServiceError() from e

    @require_auth
    async def delete(self, session_id: str) -> None:
        """Delete a session and all associated data."""
        try:
            deleted = await self.session_repo.delete(session_id)
            if not deleted:
                raise SessionNotFoundError(
                    ErrorMessages.SESSION_NOT_FOUND,
                    session_id=session_id,
                )

            f = utterance_filter().session_id.eq(session_id)
            await self.utterance_repo.delete_many(f.build())

            self.logger.info(f"Deleted session {session_id} and associated data")

        except SessionNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to delete session {session_id}: {e}")
            raise InternalSessionServiceError(ErrorMessages.SESSION_DELETE_FAILED) from e

    @require_auth
    async def list(
        self,
        doctor_id: str,
        page_index: int = 0,
        page_size: int = 20,
    ) -> builtins.list[Session]:
        """List sessions for a doctor."""
        try:
            f = session_filter().doctor_id.eq(doctor_id).created_at.desc()
            return await self.session_repo.list(
                f.build(),
                page_index=page_index,
                page_size=page_size,
            )
        except Exception as e:
            self.logger.error(f"Failed to list sessions for doctor {doctor_id}: {e}")
            raise InternalSessionServiceError() from e

    @require_auth
    async def complete(self, session_id: str) -> Session:
        """Mark session as completed."""
        try:
            session = await self.session_repo.read(session_id)
            if session is None:
                raise SessionNotFoundError(
                    ErrorMessages.SESSION_NOT_FOUND,
                    session_id=session_id,
                )

            session.complete()
            await self.session_repo.update(session)

            self.logger.info(f"Completed session {session_id}")
            return session

        except SessionNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to complete session {session_id}: {e}")
            raise InternalSessionServiceError(ErrorMessages.SESSION_UPDATE_FAILED) from e

    @require_auth
    async def cancel(self, session_id: str) -> Session:
        """Cancel a session."""
        try:
            session = await self.session_repo.read(session_id)
            if session is None:
                raise SessionNotFoundError(
                    ErrorMessages.SESSION_NOT_FOUND,
                    session_id=session_id,
                )

            session.cancel()
            await self.session_repo.update(session)

            self.logger.info(f"Cancelled session {session_id}")
            return session

        except SessionNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to cancel session {session_id}: {e}")
            raise InternalSessionServiceError(ErrorMessages.SESSION_UPDATE_FAILED) from e

    @require_auth
    async def get_utterances(
        self,
        session_id: str,
        page_index: int = 0,
        page_size: int = 100,
    ) -> builtins.list[Utterance]:
        """Get utterances for a session."""
        try:
            f = utterance_filter().session_id.eq(session_id).sequence.asc()
            return await self.utterance_repo.list(
                f.build(),
                page_index=page_index,
                page_size=page_size,
            )
        except Exception as e:
            self.logger.error(f"Failed to get utterances for session {session_id}: {e}")
            raise InternalSessionServiceError() from e

    @require_auth
    async def session(self, session_id: str) -> SessionContext:
        """Create a session context for recording."""
        try:
            user_session = await self.session_manager.get_session()
            if not user_session:
                raise NoActiveSessionError(ErrorMessages.NO_ACTIVE_SESSION)

            f = vp_filter().doctor_id.eq(user_session.doctor_id).is_active.eq(True)
            vp = await self.vp_repo.first(f.build())
            if not vp:
                raise SessionServiceError(ErrorMessages.NO_VOICEPRINT_FOUND)

            session = await self.session_repo.read(session_id)
            if session is None:
                raise SessionNotFoundError(
                    ErrorMessages.SESSION_NOT_FOUND,
                    session_id=session_id,
                )

            session.start()
            await self.session_repo.update(session)

            return SessionContext(
                config=self.config,
                session=session,
                session_repo=self.session_repo,
                segment_repo=self.segment_repo,
                utterance_repo=self.utterance_repo,
                vpr=self.vpr,
                transcription=self.transcription,
                recorder=self.recorder,
                vpr_uid=vp.vpr_uid,
            )

        except (NoActiveSessionError, SessionNotFoundError, SessionServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to create session context: {e}")
            raise InternalSessionServiceError() from e


class _VPRTask(t.NamedTuple):
    """VPR verification task."""

    sequence: int
    text: str
    started_at: float  # Absolute timestamp from Start event
    ended_at: float  # Absolute timestamp from Done event


class _UtteranceData(t.TypedDict):
    started_at: float  # Absolute timestamp from Start event
    text: str
    sequence: int | None


class SessionContext(LoggingMixin, AbstractSession):
    """Context for managing an active recording session with async
    VPR."""

    __logtag__ = "audex.service.session:SessionContext"

    def __init__(
        self,
        config: SessionServiceConfig,
        session: Session,
        session_repo: SessionRepository,
        segment_repo: SegmentRepository,
        utterance_repo: UtteranceRepository,
        vpr: VPR,
        transcription: Transcription,
        recorder: AudioRecorder,
        vpr_uid: str,
    ):
        super().__init__()
        self.config = config
        self.session = session
        self.session_repo = session_repo
        self.segment_repo = segment_repo
        self.utterance_repo = utterance_repo
        self.vpr = vpr
        self.transcription = transcription
        self.recorder = recorder
        self.vpr_uid = vpr_uid

        self.transcription_session = transcription.session(fmt="pcm", sample_rate=self.config.sr)
        self._utterance_sequence = 0

        # VPR async processing
        self._vpr_queue: asyncio.Queue[_VPRTask] = asyncio.Queue()
        self._vpr_results: dict[int, bool] = {}  # sequence -> is_doctor
        self._vpr_worker_task: asyncio.Task[None] | None = None

        # Audio streaming
        self._audio_sender_task: asyncio.Task[None] | None = None

        # Utterance tracking (utterance_id -> data)
        self._utterances: dict[str, _UtteranceData] = {}

    async def start(self) -> None:
        """Start the recording session."""
        try:
            # Start transcription
            try:
                await self.transcription_session.start()
            except TranscriptionError as e:
                self.logger.error(f"Failed to start transcription: {e}")
                raise RecordingError(ErrorMessages.TRANSCRIPTION_START_FAILED) from e

            # Start audio recording
            try:
                await self.recorder.start(self.config.audio_key_prefix, self.session.id)
            except Exception as e:
                self.logger.error(f"Failed to start recording: {e}")
                with contextlib.suppress(BaseException):
                    await self.transcription_session.close()
                raise RecordingError(ErrorMessages.RECORDING_START_FAILED) from e

            # Get current utterance sequence
            f = utterance_filter().session_id.eq(self.session.id)
            last_utterance = await self.utterance_repo.first(f.sequence.desc().build())
            self._utterance_sequence = 0 if last_utterance is None else last_utterance.sequence

            # Start VPR worker
            self._vpr_worker_task = asyncio.create_task(self._vpr_worker())

            # Start audio sender
            self._audio_sender_task = asyncio.create_task(self._audio_sender())

            self.logger.info(f"Started session context for {self.session.id}")

        except RecordingError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to start session: {e}")
            raise InternalSessionServiceError(ErrorMessages.RECORDING_START_FAILED) from e

    async def _audio_sender(self) -> None:
        """Continuously send audio frames to transcription."""
        try:
            async for frame in self.recorder.stream(
                chunk_size=self.config.sr // 10,  # 100ms chunks
                format=AudioFormat.PCM,
                rate=self.config.sr,
                channels=1,
            ):
                await self.transcription_session.send(frame)
        except asyncio.CancelledError:
            self.logger.debug("Audio sender cancelled")
        except Exception as e:
            self.logger.error(f"Audio sender error: {e}")

    async def _vpr_worker(self) -> None:
        """Background worker for VPR verification."""
        try:
            while True:
                task = await self._vpr_queue.get()

                try:
                    # Calculate audio segment time range with buffer
                    buffer_seconds = self.config.segment_buffer_ms / 1000.0
                    utterance_start = datetime.datetime.fromtimestamp(
                        task.started_at - buffer_seconds,
                        tz=datetime.UTC,
                    )
                    utterance_end = datetime.datetime.fromtimestamp(
                        task.ended_at + buffer_seconds,
                        tz=datetime.UTC,
                    )

                    # Extract audio segment
                    audio_segment = await self.recorder.segment(
                        started_at=utterance_start,
                        ended_at=utterance_end,
                        rate=self.config.vpr_sr,
                        channels=1,
                        format=AudioFormat.MP3,
                    )

                    self.logger.debug(
                        f"VPR seq={task.sequence}: extracted audio "
                        f"from {utterance_start.isoformat()} to {utterance_end.isoformat()} "
                        f"(duration={(task.ended_at - task.started_at):.2f}s)"
                    )

                    # VPR verification
                    try:
                        vpr_score = await self.vpr.verify(
                            uid=self.vpr_uid,
                            data=audio_segment,
                            sr=self.config.vpr_sr,
                        )
                        is_doctor = vpr_score >= self.config.vpr_threshold

                        self.logger.debug(
                            f"VPR seq={task.sequence}: score={vpr_score:.3f}, "
                            f"is_doctor={is_doctor}, text={task.text[:30]}..."
                        )
                    except VPRError as e:
                        self.logger.warning(f"VPR verification failed: {e}")
                        is_doctor = False

                    # Store result
                    self._vpr_results[task.sequence] = is_doctor

                    # Store utterance to database
                    await self._store_utterance(
                        sequence=task.sequence,
                        text=task.text,
                        started_at=task.started_at,
                        ended_at=task.ended_at,
                        is_doctor=is_doctor,
                    )

                except Exception as e:
                    self.logger.error(f"VPR worker error for seq={task.sequence}: {e}")
                    self._vpr_results[task.sequence] = False

                finally:
                    self._vpr_queue.task_done()

        except asyncio.CancelledError:
            self.logger.debug("VPR worker cancelled")

    async def _store_utterance(
        self,
        sequence: int,
        text: str,
        started_at: float,
        ended_at: float,
        is_doctor: bool,
    ) -> None:
        """Store utterance to database."""
        try:
            f = segment_filter().session_id.eq(self.session.id)
            current_segment = await self.segment_repo.first(f.sequence.desc().build())
            segment_id = current_segment.id if current_segment else "unknown"

            speaker = Speaker.DOCTOR if is_doctor else Speaker.PATIENT

            utterance = Utterance(
                session_id=self.session.id,
                segment_id=segment_id,
                sequence=sequence,
                speaker=speaker,
                text=text,
                confidence=None,
                start_time_ms=int(started_at * 1000),
                end_time_ms=int(ended_at * 1000),
                timestamp=utils.utcnow(),
            )

            await self.utterance_repo.create(utterance)

            self.logger.debug(
                f"Stored utterance {utterance.id} (seq={sequence}, speaker={speaker.value})"
            )

        except Exception as e:
            self.logger.error(f"Failed to store utterance seq={sequence}: {e}")

    async def close(self) -> None:
        """Close the session context."""
        try:
            # Cancel audio sender
            if self._audio_sender_task:
                self._audio_sender_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._audio_sender_task

            # Finish transcription
            try:
                await self.transcription_session.finish()
                await self.transcription_session.close()
            except Exception as e:
                self.logger.warning(f"Failed to close transcription: {e}")

            # Wait for VPR queue to finish
            if self._vpr_queue:
                await self._vpr_queue.join()

            # Cancel VPR worker
            if self._vpr_worker_task:
                self._vpr_worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._vpr_worker_task

            # Stop recorder
            try:
                segment_data = await self.recorder.stop()
            except Exception as e:
                self.logger.error(f"Failed to stop recording: {e}")
                raise RecordingError(ErrorMessages.RECORDING_STOP_FAILED) from e

            # Store segment info
            f = segment_filter().session_id.eq(self.session.id)
            last_segment = await self.segment_repo.first(f.sequence.desc().build())
            seq = 1 if last_segment is None else last_segment.sequence + 1

            segment = Segment(
                session_id=self.session.id,
                audio_key=segment_data.key,
                duration_ms=segment_data.duration_ms,
                started_at=segment_data.started_at,
                ended_at=segment_data.ended_at,
                sequence=seq,
            )

            try:
                seg_id = await self.segment_repo.create(segment)
                self.logger.info(
                    f"Stored segment {seg_id} (seq={seq}) for session {self.session.id}, "
                    f"duration={segment_data.duration_ms}ms"
                )
            except Exception as e:
                self.logger.error(f"Failed to store segment: {e}")

            # Clear audio frames
            self.recorder.clear_frames()

            # Clean up utterance tracking
            self._utterances.clear()
            self._vpr_results.clear()

        except RecordingError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to close session: {e}")
            raise InternalSessionServiceError() from e

    def receive(self) -> AsyncStream[Start | Delta | Done]:
        """Receive transcription events."""
        return AsyncStream(self._receive_iter())

    async def _receive_iter(self) -> t.AsyncIterator[Start | Delta | Done]:
        """Internal iterator for receiving transcription events."""
        async for event in self.transcription_session.receive():
            if isinstance(event, events.Start):
                # Track new utterance with absolute start time
                self._utterances[event.utterance_id] = {
                    "started_at": event.started_at,
                    "text": "",
                    "sequence": None,
                }

                yield Start(session_id=self.session.id)

            elif isinstance(event, events.Delta):
                # Update utterance tracking
                if event.utterance_id not in self._utterances:
                    self.logger.warning(
                        f"Received Delta for unknown utterance: {event.utterance_id}"
                    )
                    continue

                utt = self._utterances[event.utterance_id]

                if not event.interim:
                    # Final delta - update text
                    utt["text"] = event.text

                    # Assign sequence number
                    self._utterance_sequence += 1
                    utt["sequence"] = self._utterance_sequence

                    # Calculate absolute timestamps (only for display, not for VPR)
                    started_at = utt["started_at"]
                    from_at = started_at + event.offset_begin
                    to_at = (
                        started_at + event.offset_end
                        if event.offset_end is not None
                        else started_at + event.offset_begin + 1.0
                    )

                    # Yield Delta with sequence
                    yield Delta(
                        session_id=self.session.id,
                        from_at=from_at,
                        to_at=to_at,
                        text=event.text,
                        interim=False,
                        sequence=self._utterance_sequence,
                    )
                else:
                    # Interim result - calculate display timestamps
                    started_at = utt["started_at"]
                    from_at = started_at + event.offset_begin
                    to_at = (
                        started_at + event.offset_end
                        if event.offset_end is not None
                        else started_at + event.offset_begin + 1.0
                    )

                    yield Delta(
                        session_id=self.session.id,
                        from_at=from_at,
                        to_at=to_at,
                        text=event.text,
                        interim=True,
                        sequence=None,
                    )

            elif isinstance(event, events.Done):
                # Get utterance data
                if event.utterance_id not in self._utterances:
                    self.logger.warning(
                        f"Received Done for unknown utterance: {event.utterance_id}"
                    )
                    continue

                utt = self._utterances[event.utterance_id]
                sequence = utt.get("sequence")
                text = utt.get("text", "")

                # Only queue for VPR if we have valid data
                if sequence is not None and text:
                    # Queue VPR task using absolute timestamps from Start and Done events
                    await self._vpr_queue.put(
                        _VPRTask(
                            sequence=sequence,
                            text=text,
                            started_at=utt["started_at"],  # From Start event
                            ended_at=event.ended_at,  # From Done event
                        )
                    )

                # Check VPR result (may not be ready yet)
                is_doctor = self._vpr_results.get(sequence, False) if sequence else False

                yield Done(
                    session_id=self.session.id,
                    is_doctor=is_doctor,
                    full_text=text,
                    sequence=sequence or 0,
                )

                # Clean up to prevent memory leak
                del self._utterances[event.utterance_id]
                if sequence in self._vpr_results:
                    del self._vpr_results[sequence]
