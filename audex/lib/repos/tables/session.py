from __future__ import annotations

import datetime
import typing as t

import sqlmodel as sqlm

from audex.entity.session import Session
from audex.lib.repos.tables import BaseTable
from audex.valueobj.session import SessionStatus


class SessionTable(BaseTable[Session], table=True):
    """Session table model for SQLite storage.

    Maps the Session entity to the database table with all necessary fields
    for tracking conversation sessions, their status, and timing.

    Table: sessions
    """

    __tablename__ = "sessions"

    doctor_id: str = sqlm.Field(
        index=True,
        max_length=50,
        description="Foreign key to doctor who owns this session",
    )
    patient_name: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=100,
        description="Patient name for this session",
    )
    clinic_number: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=50,
        description="Clinic number or ID for this session",
    )
    medical_record_number: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=50,
        description="Medical record number for this session",
    )
    diagnosis: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=255,
        description="Preliminary diagnosis for this session",
    )
    status: str = sqlm.Field(
        default=SessionStatus.DRAFT.value,
        max_length=20,
        index=True,
        description="Session status (draft/in_progress/completed/cancelled)",
    )
    started_at: datetime.datetime | None = sqlm.Field(
        default=None,
        nullable=True,
        description="Timestamp when session first started",
    )
    ended_at: datetime.datetime | None = sqlm.Field(
        default=None,
        nullable=True,
        description="Timestamp when session ended",
    )
    notes: str | None = sqlm.Field(
        default=None,
        nullable=True,
        description="Additional notes about the session",
    )

    @classmethod
    def from_entity(cls, entity: Session) -> t.Self:
        """Convert Session entity to table model.

        Args:
            entity: The Session entity to convert.

        Returns:
            SessionTable instance.
        """
        return cls(
            id=entity.id,
            doctor_id=entity.doctor_id,
            patient_name=entity.patient_name,
            clinic_number=entity.clinic_number,
            medical_record_number=entity.medical_record_number,
            diagnosis=entity.diagnosis,
            status=entity.status.value,
            started_at=entity.started_at,
            ended_at=entity.ended_at,
            notes=entity.notes,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> Session:
        """Convert table model to Session entity.

        Returns:
            Session entity instance.
        """
        return Session(
            id=self.id,
            doctor_id=self.doctor_id,
            patient_name=self.patient_name,
            clinic_number=self.clinic_number,
            medical_record_number=self.medical_record_number,
            diagnosis=self.diagnosis,
            status=SessionStatus.parse(self.status),
            started_at=self.started_at,
            ended_at=self.ended_at,
            notes=self.notes,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def update(self, entity: Session) -> None:
        """Update table model fields from Session entity.

        Args:
            entity: The Session entity with updated data.
        """
        self.doctor_id = entity.doctor_id
        self.patient_name = entity.patient_name
        self.clinic_number = entity.clinic_number
        self.medical_record_number = entity.medical_record_number
        self.diagnosis = entity.diagnosis
        self.status = entity.status.value
        self.started_at = entity.started_at
        self.ended_at = entity.ended_at
        self.notes = entity.notes
        self.updated_at = entity.updated_at


TABLES: set[type[sqlm.SQLModel]] = {SessionTable}
"""Set of all table models for the repository."""
