from __future__ import annotations

import datetime

from audex import utils
from audex.entity import BaseEntity
from audex.entity import touch_after
from audex.entity.fields import DateTimeField
from audex.entity.fields import StringBackedField
from audex.entity.fields import StringField
from audex.valueobj.session import SessionStatus


class Session(BaseEntity):
    """Session entity representing a doctor-patient conversation
    session.

    Represents a single recording session where a doctor converses with a
    patient. A session can be started and stopped multiple times, creating
    multiple audio segments. Each session belongs to a specific doctor and
    tracks the overall session status and timing.

    Attributes:
        id: The unique identifier of the session. Auto-generated with "session-"
            prefix.
        doctor_id: The ID of the doctor who owns this session. Foreign key
            reference to Doctor entity.
        patient_name: The name of the patient in this session. Optional field
            for record keeping.
        clinic_number: Outpatient clinic number. Optional.
        medical_record_number: Medical record/case number. Optional.
        diagnosis: Preliminary or final diagnosis. Optional.
        status: The current status of the session (DRAFT, IN_PROGRESS, COMPLETED,
            CANCELLED). Defaults to DRAFT.
        started_at: Timestamp when the session first started recording. None
            if not yet started.
        ended_at: Timestamp when the session was completed or cancelled. None
            if still in progress or draft.
        notes: Additional notes about the session. Optional field for doctor's
            remarks.

    Inherited Attributes:
        created_at: Timestamp when the session was created.
        updated_at: Timestamp when the session was last updated.

    Example:
        ```python
        # Create new session
        session = Session(
            doctor_id="doctor-abc123",
            patient_name="李女士",
            clinic_number="20250123-001",
            medical_record_number="MR-2025-001",
            diagnosis="上呼吸道感染",
            notes="初诊",
        )

        # Start recording
        session.start()
        print(session.status)  # SessionStatus.IN_PROGRESS

        # Complete session
        session.complete()
        print(session.status)  # SessionStatus.COMPLETED
        ```
    """

    id: str = StringField(default_factory=lambda: utils.gen_id(prefix="session-"))
    doctor_id: str = StringField()
    patient_name: str | None = StringField(nullable=True)
    clinic_number: str | None = StringField(nullable=True)
    medical_record_number: str | None = StringField(nullable=True)
    diagnosis: str | None = StringField(nullable=True)
    status: SessionStatus = StringBackedField(SessionStatus, default=SessionStatus.DRAFT)
    started_at: datetime.datetime | None = DateTimeField(nullable=True)
    ended_at: datetime.datetime | None = DateTimeField(nullable=True)
    notes: str | None = StringField(nullable=True)

    @property
    def is_active(self) -> bool:
        """Check if the session is currently active (in progress).

        Returns:
            True if status is IN_PROGRESS, False otherwise.
        """
        return self.status == SessionStatus.IN_PROGRESS

    @property
    def is_finished(self) -> bool:
        """Check if the session is finished (completed or cancelled).

        Returns:
            True if status is COMPLETED or CANCELLED, False otherwise.
        """
        return self.status in (SessionStatus.COMPLETED, SessionStatus.CANCELLED)

    @touch_after
    def start(self) -> None:
        """Start the session recording.

        Sets status to IN_PROGRESS and records the start timestamp if this
        is the first time starting.

        Note:
            The updated_at timestamp is automatically updated.
        """
        if self.status == SessionStatus.DRAFT and self.started_at is None:
            self.started_at = utils.utcnow()
        self.status = SessionStatus.IN_PROGRESS

    @touch_after
    def complete(self) -> None:
        """Complete the session.

        Sets status to COMPLETED and records the end timestamp.

        Note:
            The updated_at timestamp is automatically updated.
        """
        self.status = SessionStatus.COMPLETED
        self.ended_at = utils.utcnow()

    @touch_after
    def cancel(self) -> None:
        """Cancel the session.

        Sets status to CANCELLED and records the end timestamp.

        Note:
            The updated_at timestamp is automatically updated.
        """
        self.status = SessionStatus.CANCELLED
        self.ended_at = utils.utcnow()
