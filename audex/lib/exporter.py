from __future__ import annotations

import io
import json
import pathlib
import zipfile

from audex.entity.segment import Segment
from audex.entity.session import Session
from audex.entity.utterance import Utterance
from audex.filters.generated import segment_filter
from audex.filters.generated import utterance_filter
from audex.helper.mixin import LoggingMixin
from audex.lib.repos.segment import SegmentRepository
from audex.lib.repos.session import SessionRepository
from audex.lib.repos.utterance import UtteranceRepository
from audex.lib.server.types import AudioMetadataItem
from audex.lib.server.types import AudioMetadataJSON
from audex.lib.server.types import ConversationJSON
from audex.lib.server.types import SegmentDict
from audex.lib.server.types import SessionDict
from audex.lib.server.types import SessionExportData
from audex.lib.server.types import UtteranceDict
from audex.lib.store import Store


class Exporter(LoggingMixin):
    """Exporter for packaging session data and audio files."""

    __logtag__ = "audex.lib.exporter"

    def __init__(
        self,
        session_repo: SessionRepository,
        segment_repo: SegmentRepository,
        utterance_repo: UtteranceRepository,
        store: Store,
    ):
        super().__init__()
        self.session_repo = session_repo
        self.segment_repo = segment_repo
        self.utterance_repo = utterance_repo
        self.store = store

    async def export_session_data(self, session_id: str) -> SessionExportData:
        """Export session data as structured format."""
        # Get session
        session = await self.session_repo.read(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get utterances
        utt_filter = utterance_filter().session_id.eq(session_id).sequence.asc()
        utterances = await self.utterance_repo.list(utt_filter.build())

        # Get segments
        seg_filter = segment_filter().session_id.eq(session_id).sequence.asc()
        segments = await self.segment_repo.list(seg_filter.build())

        # Convert to typed dicts
        return SessionExportData(
            session=self._session_to_dict(session),
            utterances=[self._utterance_to_dict(u) for u in utterances],
            segments=[self._segment_to_dict(s) for s in segments],
        )

    async def export_session_zip(self, session_id: str) -> bytes:
        """Export session as ZIP package."""
        export_data = await self.export_session_data(session_id)
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add conversation.json
            conversation: ConversationJSON = {
                "session": export_data["session"],
                "utterances": export_data["utterances"],
                "total_utterances": len(export_data["utterances"]),
                "total_segments": len(export_data["segments"]),
            }
            zipf.writestr(
                "conversation.json",
                json.dumps(conversation, ensure_ascii=False, indent=2),
            )

            # Add audio files
            audio_metadata_items: list[AudioMetadataItem] = []

            for idx, segment_dict in enumerate(export_data["segments"], start=1):
                audio_key = segment_dict["audio_key"]

                try:
                    audio_data = await self.store.download(audio_key)
                    ext = pathlib.Path(audio_key).suffix or ".mp3"
                    filename = f"segment_{idx:03d}{ext}"

                    zipf.writestr(f"audio/{filename}", audio_data)

                    audio_metadata_items.append(
                        AudioMetadataItem(
                            filename=filename,
                            sequence=segment_dict["sequence"],
                            duration_ms=segment_dict["duration_ms"],
                            started_at=segment_dict["started_at"],
                            ended_at=segment_dict["ended_at"],
                        )
                    )

                    self.logger.debug(f"Added audio file: {filename}")

                except Exception as e:
                    self.logger.error(f"Failed to add audio {audio_key}: {e}")

            # Add audio metadata
            if audio_metadata_items:
                audio_metadata: AudioMetadataJSON = {
                    "session_id": session_id,
                    "total_segments": len(audio_metadata_items),
                    "segments": audio_metadata_items,
                }
                zipf.writestr(
                    "audio/metadata.json",
                    json.dumps(audio_metadata, ensure_ascii=False, indent=2),
                )

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    async def export_multiple_sessions_zip(self, session_ids: list[str]) -> bytes:
        """Export multiple sessions as ZIP package."""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for session_id in session_ids:
                try:
                    session_zip_data = await self.export_session_zip(session_id)

                    with zipfile.ZipFile(io.BytesIO(session_zip_data), "r") as session_zipf:
                        for file_info in session_zipf.infolist():
                            file_data = session_zipf.read(file_info.filename)
                            new_path = f"{session_id}/{file_info.filename}"
                            zipf.writestr(new_path, file_data)

                    self.logger.info(f"Added session {session_id} to export")

                except Exception as e:
                    self.logger.error(f"Failed to export session {session_id}: {e}")

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    def _session_to_dict(self, session: Session) -> SessionDict:
        """Convert Session to typed dict."""
        return SessionDict(
            id=session.id,
            doctor_id=session.doctor_id,
            patient_name=session.patient_name,
            clinic_number=session.clinic_number,
            medical_record_number=session.medical_record_number,
            diagnosis=session.diagnosis,
            status=session.status.value,
            started_at=session.started_at.isoformat() if session.started_at else None,
            ended_at=session.ended_at.isoformat() if session.ended_at else None,
            created_at=session.created_at.isoformat(),
        )

    def _utterance_to_dict(self, utterance: Utterance) -> UtteranceDict:
        """Convert Utterance to typed dict."""
        return UtteranceDict(
            id=utterance.id,
            sequence=utterance.sequence,
            speaker=utterance.speaker.value,
            text=utterance.text,
            confidence=utterance.confidence,
            start_time_ms=utterance.start_time_ms,
            end_time_ms=utterance.end_time_ms,
            duration_ms=utterance.duration_ms,
            timestamp=utterance.timestamp.isoformat(),
        )

    def _segment_to_dict(self, segment: Segment) -> SegmentDict:
        """Convert Segment to typed dict."""
        return SegmentDict(
            id=segment.id,
            sequence=segment.sequence,
            audio_key=segment.audio_key,
            started_at=segment.started_at.isoformat(),
            ended_at=segment.ended_at.isoformat() if segment.ended_at else None,
            duration_ms=segment.duration_ms,
        )
