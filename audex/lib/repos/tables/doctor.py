from __future__ import annotations

import typing as t

import sqlmodel as sqlm

from audex.entity.doctor import Doctor
from audex.lib.repos.tables import BaseTable
from audex.valueobj.common.auth import HashedPassword
from audex.valueobj.common.email import Email


class DoctorTable(BaseTable[Doctor], table=True):
    """Doctor table model for SQLite storage.

    Maps the Doctor entity to the database table with all necessary fields
    for authentication, voiceprint management, and account status.

    Table: doctors
    """

    __tablename__ = "doctors"

    eid: str = sqlm.Field(
        ...,
        unique=True,
        index=True,
        max_length=100,
        description="Employee/staff ID in the hospital system.",
    )
    password_hash: str = sqlm.Field(
        ...,
        max_length=255,
        description="The hashed password for secure authentication.",
    )
    name: str = sqlm.Field(
        ...,
        max_length=100,
        description="The doctor's real name for display and records.",
    )
    department: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=100,
        description="Department or specialty. Optional.",
    )
    title: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=100,
        description="Professional title (e.g., Attending, Resident). Optional.",
    )
    hospital: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=150,
        description="Affiliated hospital name. Optional.",
    )
    phone: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=20,
        description="Contact phone number. Optional.",
    )
    email: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=100,
        description="Contact email address. Optional.",
    )
    is_active: bool = sqlm.Field(
        default=True,
        description="Indicates if the doctor's account is active.",
    )

    @classmethod
    def from_entity(cls, entity: Doctor) -> t.Self:
        """Convert Doctor entity to table model.

        Args:
            entity: The Doctor entity to convert.

        Returns:
            DoctorTable instance.
        """
        return cls(
            id=entity.id,
            eid=entity.eid,
            password_hash=entity.password_hash.value,
            name=entity.name,
            department=entity.department,
            title=entity.title,
            hospital=entity.hospital,
            phone=entity.phone,
            email=entity.email.value,
            is_active=entity.is_active,
        )

    def to_entity(self) -> Doctor:
        """Convert table model to Doctor entity.

        Returns:
            Doctor entity instance.
        """
        return Doctor(
            id=self.id,
            eid=self.eid,
            password_hash=HashedPassword.parse(self.password_hash, validate=False),
            name=self.name,
            department=self.department,
            title=self.title,
            hospital=self.hospital,
            phone=self.phone,
            email=Email.parse(self.email, validate=False),
            is_active=self.is_active,
        )


TABLES: set[type[sqlm.SQLModel]] = {DoctorTable}
"""Set of all table models for the repository."""
