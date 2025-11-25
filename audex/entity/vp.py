from __future__ import annotations

from audex import utils
from audex.entity import BaseEntity
from audex.entity.fields import BoolField
from audex.entity.fields import IntegerField
from audex.entity.fields import StringField


class VP(BaseEntity):
    """Voiceprint registration record entity.

    Represents a voiceprint registration in the VPR system. Links a doctor
    to their registered voiceprint in the external VPR service, storing
    both the local audio reference and remote VPR identifiers.

    This entity allows for VPR system migration without requiring doctors
    to re-register their voiceprints - the local audio can be re-uploaded
    to a new VPR system.

    Attributes:
        id: The unique identifier of the registration. Auto-generated with
            "vp_reg-" prefix.
        doctor_id: The ID of the doctor who owns this voiceprint. Foreign
            key reference to Doctor entity.
        vpr_uid: The unique identifier in the VPR system for this voiceprint.
            Used for 1:1 speaker verification.
        vpr_group_id: The group ID in the VPR system. Optional for organizing
            voiceprints (e.g., by hospital or department).
        audio_key: Local storage key for the voiceprint audio file. Preserved
            for potential re-registration with different VPR systems.
        text_content: The text that was read during voiceprint registration.
            Stored for potential re-registration requirements.
        sample_rate: Audio sample rate used for registration (8000 or 16000 Hz).
        is_active: Whether this registration is currently active. Only one
            active registration per doctor should exist.

    Inherited Attributes:
        created_at: Timestamp when the registration was created.
        updated_at: Timestamp when the registration was last updated.

    Example:
        ```python
        # Create voiceprint registration after VPR API call
        registration = VPRegistration(
            doctor_id="doctor-abc123",
            vpr_uid="vpr_user_xyz789",
            vpr_group_id="hospital_001",
            audio_key="vp/doctor-abc123/registration.wav",
            text_content="请朗读以下文本进行声纹注册...",
            sample_rate=16000,
            is_active=True,
        )

        # Check if active
        if registration.is_active:
            print(f"Active VPR UID: {registration.vpr_uid}")
        ```
    """

    id: str = StringField(default_factory=lambda: utils.gen_id(prefix="vp_reg-"))
    doctor_id: str = StringField()
    vpr_uid: str = StringField()
    vpr_group_id: str | None = StringField(nullable=True)
    audio_key: str = StringField()
    text_content: str = StringField()
    sample_rate: int = IntegerField()
    is_active: bool = BoolField(default=True)
