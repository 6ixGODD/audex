from __future__ import annotations

from audex import utils
from audex.entity import BaseEntity
from audex.entity.fields import StringField


class VoiceprintRegistration(BaseEntity):
    """VoiceprintRegistration entity representing a doctor's voiceprint
    registration in the VPR system.

    This entity tracks the registration details for integrating with the
    Voice Print Recognition (VPR) system. It stores the VPR-specific
    identifiers and configuration needed for voice verification.

    Attributes:
        id: The unique identifier of the registration. Auto-generated with
            "vpr-" prefix.
        doctor_id: The ID of the doctor this registration belongs to. Foreign
            key reference to Doctor entity.
        vp_id: The voiceprint ID returned by the VPR system. Used for
            verification requests.
        vpr_group_id: The group ID in the VPR system where the voiceprint is
            registered. Used to organize voiceprints in the VPR backend.
        vpr_system: The name/type of the VPR system being used (e.g., "xfyun",
            "unisound"). Allows switching between different VPR providers.
        registration_address: The URL or endpoint of the VPR service used for
            registration. Stored for audit and troubleshooting.

    Inherited Attributes:
        created_at: Timestamp when the registration was created.
        updated_at: Timestamp when the registration was last updated.

    Example:
        ```python
        # Create registration after successful VPR enrollment
        registration = VoiceprintRegistration(
            doctor_id="doctor-abc123",
            vp_id="vp_8a7f9d3e2b1c",
            vpr_group_id="group_hospital_001",
            vpr_system="xfyun",
            registration_address="https://api.xfyun.cn/v1/vpr",
        )

        # Update registration if re-enrolling
        registration.vp_id = "vp_new_id_here"
        registration.touch()
        ```
    """

    id: str = StringField(immutable=True, default_factory=lambda: utils.gen_id(prefix="vpr-"))
    doctor_id: str = StringField()
    vp_id: str = StringField()
    vpr_group_id: str = StringField()
    vpr_system: str = StringField()
    registration_address: str = StringField()
