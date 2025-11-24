from __future__ import annotations

import sqlmodel as sqlm

from audex.entity.vp import VP
from audex.lib.repos.tables import BaseTable


class VPTable(BaseTable[VP], table=True):
    """Voiceprint (VP) table model for SQLite storage.

    Maps the VP entity to the database table with fields for managing
    voiceprint data associated with doctors.

    Table: vps
    """

    __tablename__ = "vps"

    doctor_id: str = sqlm.Field(
        ...,
        index=True,
        foreign_key="doctors.id",
        max_length=50,
        description="The ID of the doctor associated with this voiceprint.",
    )
    vpr_uid: str = sqlm.Field(
        ...,
        unique=True,
        index=True,
        max_length=100,
        description="Unique voiceprint recognition UID from the VP service.",
    )
    vpr_group_id: str = sqlm.Field(
        ...,
        index=True,
        max_length=100,
        description="Voiceprint recognition group ID from the VP service.",
    )
    audio_key: str = sqlm.Field(
        ...,
        unique=True,
        index=True,
        max_length=150,
        description="Storage key for the voiceprint audio file.",
    )
    text_content: str = sqlm.Field(
        ...,
        max_length=500,
        description="The text content used for voiceprint enrollment.",
    )
    is_active: bool = sqlm.Field(
        default=True,
        description="Indicates whether the voiceprint is active for recognition.",
    )

    @classmethod
    def from_entity(cls, entity: VP) -> VPTable:
        """Create a VPTable instance from a VP entity."""
        return cls(
            id=entity.id,
            doctor_id=entity.doctor_id,
            vpr_uid=entity.vpr_uid,
            vpr_group_id=entity.vpr_group_id,
            audio_key=entity.audio_key,
            text_content=entity.text_content,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> VP:
        return VP(
            id=self.id,
            doctor_id=self.doctor_id,
            vpr_uid=self.vpr_uid,
            vpr_group_id=self.vpr_group_id,
            audio_key=self.audio_key,
            text_content=self.text_content,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
