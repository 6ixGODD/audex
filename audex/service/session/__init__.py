from __future__ import annotations

import builtins
import datetime
import typing as t

from audex import utils
from audex.entity.segment import Segment
from audex.entity.session import Session
from audex.entity.utterance import Utterance
from audex.filters.generated import segment_filter
from audex.filters.generated import session_filter
from audex.filters.generated import utterance_filter
from audex.filters.generated import vp_filter
from audex.helper.mixin import LoggingMixin
from audex.helper.stream import AsyncStream
from audex.lib.recorder import AudioRecorder
from audex.lib.repos.segment import SegmentRepository
from audex.lib.repos.session import SessionRepository
from audex.lib.repos.utterance import UtteranceRepository
from audex.lib.repos.vp import VPRepository
from audex.lib.session import SessionManager
from audex.lib.transcription import Transcription
from audex.lib.transcription import events
from audex.lib.vpr import VPR
from audex.service import BaseService
from audex.service.decorators import require_auth
from audex.service.session.exceptions import SessionNotFoundError
from audex.service.session.exceptions import SessionServiceError
from audex.service.session.types import CreateSessionCommand
from audex.service.session.types import Delta
from audex.service.session.types import Done
from audex.service.session.types import Start
from audex.types import DuplexAbstractSession
from audex.valueobj.utterance import Speaker


class SessionServiceConfig(t.NamedTuple):
    """SessionService configuration.

    Attributes:
        audio_key_prefix: Prefix for audio file keys in storage.
        segment_buffer_ms: Buffer time (ms) to add before/after utterance for VPR.
        vpr_sr: Sample rate for VPR verification.
        vpr_threshold: Threshold for speaker verification (0-1, higher = stricter).
    """

    audio_key_prefix: str = "audio"
    segment_buffer_ms: int = 200
    vpr_sr: int = 16000
    vpr_threshold: float = 0.6


class SessionService(BaseService):
    """Service for managing recording sessions.

    Handles session lifecycle, recording, transcription, and speaker
    identification.
    """

    __logtag__ = "audex.service.session"

    def __init__(
        self,
        session_manager: SessionManager,
        config: SessionServiceConfig,
        session_repo: SessionRepository,
        segment_repo: SegmentRepository,
        utterance_repo: UtteranceRepository,
        vp_repo: VPRepository,
        vpr: VPR,
        transcription: Transcription,
        recorder: AudioRecorder,
    ):
        super().__init__(session_manager=session_manager)
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
            raise SessionServiceError("Failed to create session")

        self.logger.info(f"Created session {uid} for doctor {command.doctor_id}")
        return session

    @require_auth
    async def get(self, session_id: str) -> Session | None:
        """Get session by ID."""
        return await self.session_repo.read(session_id)

    @require_auth
    async def delete(self, session_id: str) -> None:
        """Delete a session and all associated data."""
        deleted = await self.session_repo.delete(session_id)
        if not deleted:
            raise SessionNotFoundError(session_id=session_id)

        # Also delete associated utterances
        f = utterance_filter().session_id.eq(session_id)
        await self.utterance_repo.delete_many(f.build())

        self.logger.info(f"Deleted session {session_id} and associated data")

    @require_auth
    async def list(
        self,
        doctor_id: str,
        page_index: int = 0,
        page_size: int = 20,
    ) -> builtins.list[Session]:
        f = session_filter().doctor_id.eq(doctor_id).created_at.desc()
        return await self.session_repo.list(
            f.build(),
            page_index=page_index,
            page_size=page_size,
        )

    @require_auth
    async def complete(self, session_id: str) -> Session:
        """Mark session as completed."""
        session = await self.session_repo.read(session_id)
        if session is None:
            raise SessionNotFoundError(session_id=session_id)

        session.complete()
        await self.session_repo.update(session)

        self.logger.info(f"Completed session {session_id}")
        return session

    @require_auth
    async def cancel(self, session_id: str) -> Session:
        session = await self.session_repo.read(session_id)
        if session is None:
            raise SessionNotFoundError(session_id=session_id)

        session.cancel()
        await self.session_repo.update(session)

        self.logger.info(f"Cancelled session {session_id}")
        return session

    @require_auth
    async def get_utterances(
        self,
        session_id: str,
        page_index: int = 0,
        page_size: int = 100,
    ) -> builtins.list[Utterance]:
        f = utterance_filter().session_id.eq(session_id).sequence.asc()
        return await self.utterance_repo.list(
            f.build(),
            page_index=page_index,
            page_size=page_size,
        )

    @require_auth
    async def session(self, session_id: str) -> SessionContext:
        s = await self.session_manager.get_session()
        if not s:
            raise SessionServiceError("No active session found")
        f = vp_filter().doctor_id.eq(s.doctor_id)
        vp = await self.vp_repo.first(f.build())
        if not vp:
            raise SessionServiceError(f"No VP found for doctor {s.doctor_id}")
        session = await self.session_repo.read(session_id)
        if session is None:
            raise SessionNotFoundError(session_id=session_id)

        # Update session status to IN_PROGRESS
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


class SessionContext(LoggingMixin, DuplexAbstractSession[bytes, Start | Delta | Done]):
    """Context for managing an active recording session.

    Handles audio recording, transcription, speaker identification, and
    utterance storage.
    """

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

        self.transcription_session = transcription.session()
        self._utterance_sequence = 0

        # Track utterance info for Done event
        # Delta is cumulative, so we only need to track the latest
        self._current_utterance_start: float | None = None
        self._current_utterance_end: float | None = None
        self._current_full_text: str = ""  # Latest full text from Delta

    async def start(self) -> None:
        """Start the recording session."""
        # Start transcription session
        await self.transcription_session.start()

        # Start audio recording
        await self.recorder.start(self.config.audio_key_prefix, self.session.id)

        # Get current utterance sequence
        f = utterance_filter().session_id.eq(self.session.id)
        last_utterance = await self.utterance_repo.first(f.sequence.desc().build())
        self._utterance_sequence = 0 if last_utterance is None else last_utterance.sequence

        self.logger.info(f"Started session container for {self.session.id}")

    async def finish(self) -> None:
        """Finish the transcription session."""
        await self.transcription_session.finish()
        self.logger.info(f"Finished transcription for session {self.session.id}")

    async def close(self) -> None:
        """Close the session container."""
        # Close transcription session
        await self.transcription_session.close()

        # Stop recorder and get segment info
        segment_data = await self.recorder.stop()

        # Determine segment sequence
        f = segment_filter().session_id.eq(self.session.id)
        last_segment = await self.segment_repo.first(f.sequence.desc().build())
        seq = 1 if last_segment is None else last_segment.sequence + 1

        # Store segment info in repository
        segment = Segment(
            session_id=self.session.id,
            audio_key=segment_data.key,
            duration_ms=segment_data.duration_ms,
            started_at=segment_data.started_at,
            ended_at=segment_data.ended_at,
            sequence=seq,
        )

        seg_id = await self.segment_repo.create(segment)

        self.logger.info(
            f"Stored segment {seg_id} (seq={seq}) for session {self.session.id}, "
            f"duration={segment_data.duration_ms}ms"
        )

        # Clear audio frames to free memory
        self.recorder.clear_frames()

    async def send(self, message: bytes) -> None:
        """Send audio data to transcription service."""
        await self.transcription_session.send(message)

    def receive(self) -> AsyncStream[Start | Delta | Done]:
        """Receive transcription events."""
        return AsyncStream(self._receive_iter())

    async def _receive_iter(self) -> t.AsyncIterator[Start | Delta | Done]:
        """Internal iterator for receiving and processing transcription
        events."""
        async for event in self.transcription_session.receive():
            if isinstance(event, events.Start):
                # Reset utterance tracking
                self._current_utterance_start = None
                self._current_utterance_end = None
                self._current_full_text = ""

                yield Start(session_id=self.session.id)

            elif isinstance(event, events.Delta):
                # Track utterance timing
                if self._current_utterance_start is None:
                    self._current_utterance_start = event.from_at

                self._current_utterance_end = event.to_at

                # Delta is cumulative - just keep the latest full text
                if not event.interim:
                    self._current_full_text = event.text

                # Just pass through Delta events without speaker identification
                yield Delta(
                    session_id=self.session.id,
                    from_at=event.from_at,
                    to_at=event.to_at,
                    text=event.text,
                    interim=event.interim,
                )

            elif isinstance(event, events.Done):
                # Now do speaker identification once for the complete utterance
                is_doctor = False
                full_text = self._current_full_text
                vpr_score: float | None = None

                if (
                    self._current_utterance_start is not None
                    and self._current_utterance_end is not None
                    and full_text  # Only do VPR if we have text
                ):
                    try:
                        # Add buffer before/after for better VPR accuracy
                        buffer_seconds = self.config.segment_buffer_ms / 1000.0

                        utterance_start = datetime.datetime.fromtimestamp(
                            self._current_utterance_start - buffer_seconds,
                            tz=datetime.UTC,
                        )
                        utterance_end = datetime.datetime.fromtimestamp(
                            self._current_utterance_end + buffer_seconds,
                            tz=datetime.UTC,
                        )

                        # Get audio segment and resample for VPR
                        audio_segment = await self.recorder.segment(
                            started_at=utterance_start,
                            ended_at=utterance_end,
                            rate=self.config.vpr_sr,
                            channels=1,  # VPR usually needs mono
                        )

                        # Verify speaker with VPR (only once!)
                        vpr_score = await self.vpr.verify(
                            uid=self.vpr_uid,
                            data=audio_segment,
                            sr=self.config.vpr_sr,
                        )

                        # Determine speaker based on threshold
                        is_doctor = vpr_score >= self.config.vpr_threshold

                        self.logger.debug(
                            f"VPR score: {vpr_score:.3f}, "
                            f"is_doctor: {is_doctor}, "
                            f"text: {full_text[:50]}..."
                        )

                    except Exception as e:
                        self.logger.warning(
                            f"Failed to verify speaker for utterance: {e}",
                            exc_info=True,
                        )
                        # Keep default (is_doctor=False, i.e., patient)

                    # Store utterance in database
                    try:
                        self._utterance_sequence += 1

                        # Get current segment
                        f = segment_filter().session_id.eq(self.session.id)
                        current_segment = await self.segment_repo.first(f.sequence.desc().build())

                        segment_id = current_segment.id if current_segment else "unknown"

                        speaker = Speaker.DOCTOR if is_doctor else Speaker.PATIENT

                        utterance = Utterance(
                            session_id=self.session.id,
                            segment_id=segment_id,
                            sequence=self._utterance_sequence,
                            speaker=speaker,
                            text=full_text,
                            confidence=vpr_score,
                            start_time_ms=int(self._current_utterance_start * 1000),
                            end_time_ms=int(self._current_utterance_end * 1000),
                            timestamp=utils.utcnow(),
                        )

                        await self.utterance_repo.create(utterance)

                        self.logger.debug(
                            f"Stored utterance {utterance.id} "
                            f"(seq={self._utterance_sequence}, "
                            f"speaker={speaker.value})"
                        )

                    except Exception as e:
                        self.logger.error(
                            f"Failed to store utterance: {e}",
                            exc_info=True,
                        )

                # Yield Done event with speaker info
                yield Done(
                    session_id=self.session.id,
                    is_doctor=is_doctor,
                    full_text=full_text,
                )

                # Reset tracking for next utterance
                self._current_utterance_start = None
                self._current_utterance_end = None
                self._current_full_text = ""
