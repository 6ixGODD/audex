from __future__ import annotations

import typing as t


class CreateSessionCommand(t.NamedTuple):
    """Command for creating a new session."""

    doctor_id: str
    patient_name: str | None = None
    clinic_number: str | None = None
    medical_record_number: str | None = None
    diagnosis: str | None = None
    notes: str | None = None


class Start:
    """Transcription started event."""

    __slots__ = ("session_id",)

    def __init__(self, *, session_id: str):
        self.session_id = session_id


class Delta:
    """Transcription delta event with optional sequence number.

    Attributes:
        session_id: Session ID.
        from_at: Start timestamp.
        to_at: End timestamp.
        text: Transcribed text.
        interim: Whether this is an interim result.
        sequence: Utterance sequence number (None for interim results).
    """

    __slots__ = ("from_at", "interim", "sequence", "session_id", "text", "to_at")

    def __init__(
        self,
        *,
        session_id: str,
        from_at: float,
        to_at: float,
        text: str,
        interim: bool,
        sequence: int | None = None,
    ):
        self.session_id = session_id
        self.from_at = from_at
        self.to_at = to_at
        self.text = text
        self.interim = interim
        self.sequence = sequence


class Done:
    """Transcription completed event with speaker identification.

    Attributes:
        session_id: Session ID.
        is_doctor: Whether the speaker is the doctor.
        full_text: Full transcribed text.
        sequence: Utterance sequence number.
    """

    __slots__ = ("full_text", "is_doctor", "sequence", "session_id")

    def __init__(self, *, session_id: str, is_doctor: bool, full_text: str, sequence: int):
        self.session_id = session_id
        self.is_doctor = is_doctor
        self.full_text = full_text
        self.sequence = sequence
