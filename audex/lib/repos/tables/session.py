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
        foreign_key="doctors.uid",
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
    outpatient_number: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=50,
        description="Outpatient number (门诊号)",
    )
    medical_record_number: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=50,
        description="Medical record number (病历号)",
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
            uid=entity.id,
            doctor_id=entity.doctor_id,
            patient_name=entity.patient_name,
            outpatient_number=entity.outpatient_number,
            medical_record_number=entity.medical_record_number,
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
            id=self.uid,
            doctor_id=self.doctor_id,
            patient_name=self.patient_name,
            outpatient_number=self.outpatient_number,
            medical_record_number=self.medical_record_number,
            status=SessionStatus.parse(self.status),
            started_at=self.started_at,
            ended_at=self.ended_at,
            notes=self.notes,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


TABLES: set[type[sqlm.SQLModel]] = {SessionTable}
"""Set of all table models for the repository."""
