from __future__ import annotations

import typing as t

import sqlmodel as sqlm

from audex.entity.doctor import Doctor
from audex.lib.repos.tables import BaseTable


class DoctorTable(BaseTable[Doctor], table=True):
    """Doctor table model for SQLite storage.

    Maps the Doctor entity to the database table with all necessary fields
    for authentication, voiceprint management, and account status.

    Table: doctors
    """

    __tablename__ = "doctors"

    username: str = sqlm.Field(
        unique=True,
        index=True,
        max_length=100,
        description="Unique username for login",
    )
    password_hash: str = sqlm.Field(
        max_length=255,
        description="Hashed password for authentication",
    )
    name: str = sqlm.Field(
        max_length=100,
        description="Doctor's real name",
    )
    employee_number: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=50,
        description="Doctor's employee number (工号)",
    )
    department: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=100,
        description="Department where doctor works (科室)",
    )
    hospital_name: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=200,
        description="Name of the hospital",
    )
    vp_key: str | None = sqlm.Field(
        default=None,
        nullable=True,
        max_length=500,
        description="Voiceprint audio file key/path",
    )
    vp_text: str | None = sqlm.Field(
        default=None,
        nullable=True,
        description="Voiceprint registration text content",
    )
    is_active: bool = sqlm.Field(
        default=True,
        nullable=False,
        description="Account active status",
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
            uid=entity.id,
            username=entity.username,
            password_hash=entity.password_hash,
            name=entity.name,
            employee_number=entity.employee_number,
            department=entity.department,
            hospital_name=entity.hospital_name,
            vp_key=entity.vp_key,
            vp_text=entity.vp_text,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> Doctor:
        """Convert table model to Doctor entity.

        Returns:
            Doctor entity instance.
        """
        return Doctor(
            id=self.uid,
            username=self.username,
            password_hash=self.password_hash,
            name=self.name,
            employee_number=self.employee_number,
            department=self.department,
            hospital_name=self.hospital_name,
            vp_key=self.vp_key,
            vp_text=self.vp_text,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


TABLES: set[type[sqlm.SQLModel]] = {DoctorTable}
"""Set of all table models for the repository."""
