from __future__ import annotations

import typing as t

import sqlmodel as sqlm

from audex.entity.voiceprint_registration import VoiceprintRegistration
from audex.lib.repos.tables import BaseTable


class VoiceprintRegistrationTable(BaseTable[VoiceprintRegistration], table=True):
    """VoiceprintRegistration table model for SQLite storage.

    Maps the VoiceprintRegistration entity to the database table with all
    necessary fields for VPR system integration.

    Table: voiceprint_registrations
    """

    __tablename__ = "voiceprint_registrations"

    doctor_id: str = sqlm.Field(
        foreign_key="doctors.uid",
        index=True,
        max_length=50,
        description="Foreign key to doctor",
    )
    vp_id: str = sqlm.Field(
        max_length=100,
        description="VPR system voiceprint ID",
    )
    vpr_group_id: str = sqlm.Field(
        max_length=100,
        description="VPR system group ID",
    )
    vpr_system: str = sqlm.Field(
        max_length=50,
        description="VPR system type (e.g., xfyun, unisound)",
    )
    registration_address: str = sqlm.Field(
        max_length=500,
        description="VPR service endpoint URL",
    )

    @classmethod
    def from_entity(cls, entity: VoiceprintRegistration) -> t.Self:
        """Convert VoiceprintRegistration entity to table model.

        Args:
            entity: The VoiceprintRegistration entity to convert.

        Returns:
            VoiceprintRegistrationTable instance.
        """
        return cls(
            uid=entity.id,
            doctor_id=entity.doctor_id,
            vp_id=entity.vp_id,
            vpr_group_id=entity.vpr_group_id,
            vpr_system=entity.vpr_system,
            registration_address=entity.registration_address,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> VoiceprintRegistration:
        """Convert table model to VoiceprintRegistration entity.

        Returns:
            VoiceprintRegistration entity instance.
        """
        return VoiceprintRegistration(
            id=self.uid,
            doctor_id=self.doctor_id,
            vp_id=self.vp_id,
            vpr_group_id=self.vpr_group_id,
            vpr_system=self.vpr_system,
            registration_address=self.registration_address,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


TABLES: set[type[sqlm.SQLModel]] = {VoiceprintRegistrationTable}
"""Set of all table models for the repository."""
