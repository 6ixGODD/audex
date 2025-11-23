from __future__ import annotations

import json
import os
import pathlib
import typing as t

from audex.entity.segment import Segment
from audex.entity.session import Session
from audex.entity.utterance import Utterance
from audex.lib.database.sqlite import SQLite
from audex.lib.repos.segment import SegmentRepository
from audex.lib.repos.session import SessionRepository
from audex.lib.repos.utterance import UtteranceRepository
from audex.lib.store import Store
from audex.service import BaseService


class ExportService(BaseService):
    """Export service for organizing and exporting session data.

    This service handles exporting conversation sessions to USB devices or
    other storage locations. It organizes files in a structured format and
    exports conversation data as JSON.

    Attributes:
        session_repo: Repository for session data.
        segment_repo: Repository for segment data.
        utterance_repo: Repository for utterance data.
        store: Storage system for audio files.
    """

    __logtag__ = "ExportService"

    def __init__(
        self,
        sqlite: SQLite,
        store: Store,
    ) -> None:
        """Initialize the export service.

        Args:
            sqlite: SQLite database connection.
            store: Storage system for audio files.
        """
        super().__init__()
        self.session_repo = SessionRepository(sqlite)
        self.segment_repo = SegmentRepository(sqlite)
        self.utterance_repo = UtteranceRepository(sqlite)
        self.store = store

    async def export_session(
        self,
        session_id: str,
        export_path: str | pathlib.Path,
        include_audio: bool = True,
    ) -> dict[str, t.Any]:
        """Export a session to the specified path.

        Creates a structured directory with conversation JSON and audio files.
        Directory structure:
        ```
        {export_path}/{session_id}/
            conversation.json
            audio/
                segment-001.wav
                segment-002.wav
                ...
        ```

        Args:
            session_id: The ID of the session to export.
            export_path: Base path where the session should be exported.
            include_audio: Whether to export audio files (default: True).

        Returns:
            A dictionary with export statistics and file paths.

        Raises:
            ValueError: If session not found.
            IOError: If export path is not accessible.
        """
        self.logger.info(f"Exporting session {session_id} to {export_path}")

        # Retrieve session
        session = await self.session_repo.read(session_id)
        if session is None:
            self.logger.error(f"Session not found: {session_id}")
            raise ValueError(f"Session with ID '{session_id}' not found")

        # Create export directory
        export_path = pathlib.Path(export_path)
        session_dir = export_path / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Export conversation as JSON
        conversation_data = await self._build_conversation_json(session)
        conversation_file = session_dir / "conversation.json"
        with open(conversation_file, "w", encoding="utf-8") as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Conversation JSON exported to: {conversation_file}")

        # Export audio files if requested
        audio_files: list[str] = []
        if include_audio:
            audio_dir = session_dir / "audio"
            audio_dir.mkdir(exist_ok=True)
            audio_files = await self._export_audio_files(session_id, audio_dir)
            self.logger.info(f"Exported {len(audio_files)} audio files")

        export_stats = {
            "session_id": session_id,
            "export_path": str(session_dir),
            "conversation_file": str(conversation_file),
            "audio_files": audio_files,
            "audio_count": len(audio_files),
        }

        self.logger.info(f"Session export completed: {session_id}")
        return export_stats

    async def _build_conversation_json(self, session: Session) -> dict[str, t.Any]:
        """Build the conversation JSON structure.

        Args:
            session: The session entity.

        Returns:
            Dictionary with conversation data.
        """
        # Retrieve all utterances for the session
        # Note: Using a large page size to get all utterances in one call
        # For production use with very long sessions, consider implementing
        # pagination or streaming export
        utterances = await self.utterance_repo.list(
            Utterance.filter().session_id.eq(session.id),
            page_index=0,
            page_size=100000,  # Large enough for most sessions
        )

        # Sort utterances by sequence
        utterances.sort(key=lambda u: u.sequence)

        # Build conversation structure
        conversation = {
            "session_id": session.id,
            "doctor_id": session.doctor_id,
            "patient_name": session.patient_name,
            "outpatient_number": session.outpatient_number,
            "medical_record_number": session.medical_record_number,
            "status": session.status.value,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "notes": session.notes,
            "created_at": session.created_at.isoformat(),
            "utterances": [
                {
                    "sequence": u.sequence,
                    "speaker": u.speaker.value,
                    "text": u.text,
                    "confidence": u.confidence,
                    "start_time_ms": u.start_time_ms,
                    "end_time_ms": u.end_time_ms,
                    "duration_ms": u.duration_ms,
                    "timestamp": u.timestamp.isoformat(),
                }
                for u in utterances
            ],
        }

        return conversation

    async def _export_audio_files(
        self, session_id: str, audio_dir: pathlib.Path
    ) -> list[str]:
        """Export audio segment files for a session.

        Args:
            session_id: The ID of the session.
            audio_dir: Directory to export audio files to.

        Returns:
            List of exported audio file paths.
        """
        # Retrieve all segments for the session
        # Note: Using a large page size to get all segments in one call
        # Most sessions will have fewer than 10000 segments
        segments = await self.segment_repo.list(
            Segment.filter().session_id.eq(session_id),
            page_index=0,
            page_size=10000,  # Large enough for most sessions
        )

        # Sort segments by sequence
        segments.sort(key=lambda s: s.sequence)

        exported_files: list[str] = []
        for segment in segments:
            # Download audio from storage
            try:
                audio_data = await self.store.download(segment.audio_key)
                if isinstance(audio_data, bytes):
                    # Save to export directory
                    filename = f"segment-{segment.sequence:03d}.wav"
                    audio_file = audio_dir / filename
                    with open(audio_file, "wb") as f:
                        f.write(audio_data)
                    exported_files.append(str(audio_file))
                    self.logger.debug(f"Exported audio file: {audio_file}")
            except Exception as e:
                self.logger.warning(f"Failed to export audio for segment {segment.id}: {e}")

        return exported_files

    async def export_to_usb(
        self,
        session_id: str,
        usb_mount_point: str | pathlib.Path,
    ) -> dict[str, t.Any]:
        """Export a session to a USB device.

        This is a convenience method that exports to a USB mount point,
        typically /media/usb or similar.

        Args:
            session_id: The ID of the session to export.
            usb_mount_point: Path to the USB device mount point.

        Returns:
            A dictionary with export statistics.

        Raises:
            ValueError: If session not found.
            IOError: If USB device is not accessible.
        """
        usb_path = pathlib.Path(usb_mount_point)
        if not usb_path.exists() or not usb_path.is_dir():
            raise IOError(f"USB device not accessible at: {usb_mount_point}")

        self.logger.info(f"Exporting session {session_id} to USB at {usb_mount_point}")

        # Create a timestamped export directory on USB
        export_base = usb_path / "audex_exports"
        export_base.mkdir(exist_ok=True)

        return await self.export_session(session_id, export_base, include_audio=True)
