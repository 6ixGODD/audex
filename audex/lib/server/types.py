from __future__ import annotations

import typing as t


class SessionDict(t.TypedDict):
    """Session data structure."""

    id: str
    doctor_id: str
    patient_name: str | None
    clinic_number: str | None
    medical_record_number: str | None
    diagnosis: str | None
    status: str
    started_at: str | None
    ended_at: str | None
    created_at: str


class UtteranceDict(t.TypedDict):
    """Utterance data structure."""

    id: str
    sequence: int
    speaker: str
    text: str
    confidence: float | None
    start_time_ms: int
    end_time_ms: int
    duration_ms: int
    timestamp: str


class SegmentDict(t.TypedDict):
    """Segment data structure."""

    id: str
    sequence: int
    audio_key: str
    started_at: str
    ended_at: str | None
    duration_ms: int | None


class SessionExportData(t.TypedDict):
    """Complete session export data."""

    session: SessionDict
    utterances: list[UtteranceDict]
    segments: list[SegmentDict]


class ConversationJSON(t.TypedDict):
    """conversation.json format."""

    session: SessionDict
    utterances: list[UtteranceDict]
    total_utterances: int
    total_segments: int


class AudioMetadataItem(t.TypedDict):
    """Audio file metadata item."""

    filename: str
    sequence: int
    duration_ms: int | None
    started_at: str
    ended_at: str | None


class AudioMetadataJSON(t.TypedDict):
    """audio/metadata.json format."""

    session_id: str
    total_segments: int
    segments: list[AudioMetadataItem]


class SessionListResponse(t.TypedDict):
    """API response for session list."""

    sessions: list[SessionDict]
    total: int
    page: int
    page_size: int


class ErrorResponse(t.TypedDict):
    """API error response."""

    error: str
    details: str | None


class ExportMultipleRequest(t.TypedDict):
    """Request body for exporting multiple sessions."""

    session_ids: list[str]


class LoginRequest(t.TypedDict):
    """Login request body."""

    eid: str
    password: str


class LoginResponse(t.TypedDict):
    """Login response."""

    success: bool
    doctor_id: str | None
    doctor_name: str | None


class DoctorSessionData(t.TypedDict):
    """Doctor session data stored in cookie."""

    doctor_id: str
    eid: str
    doctor_name: str
