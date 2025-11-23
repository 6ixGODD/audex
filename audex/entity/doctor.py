from __future__ import annotations

from audex import utils
from audex.entity import BaseEntity
from audex.entity.fields import BoolField
from audex.entity.fields import StringField


class Doctor(BaseEntity):
    """Doctor entity representing a registered doctor account.

    Represents a doctor who can log in, register voiceprint, create sessions,
    and record conversations. This entity serves as the primary user identity
    for the clinic voice recording system.

    Attributes:
        id: The unique identifier of the doctor. Auto-generated with "doctor-"
            prefix for clear categorization.
        username: The unique username of the doctor for login.
        password_hash: The hashed password for secure authentication.
        name: The doctor's real name for display and records.
        employee_number: The doctor's employee number (工号) in the hospital.
            Optional field for hospital staff identification.
        department: The department (科室) where the doctor works.
            Optional field for organizational tracking.
        hospital_name: The name of the hospital where the doctor works.
            Optional field for multi-hospital systems.
        vp_key: The voiceprint audio file key/path in storage. Used for 1:1
            speaker verification to distinguish doctor from patient. None if
            not yet registered.
        vp_text: The text content that was read during voiceprint registration.
            Stored for potential re-registration with different VPR systems.
        is_active: Indicates whether the doctor account is active. Boolean flag
            controlling login ability, defaults to True.

    Inherited Attributes:
        created_at: Timestamp when the doctor account was created.
        updated_at: Timestamp when the doctor account was last updated.

    Example:
        ```python
        # Create new doctor
        doctor = Doctor(
            username="dr_zhang",
            password_hash="hashed_password_here",
            name="张医生",
            employee_number="H12345",
            department="内科",
            hospital_name="市人民医院",
            is_active=True,
        )

        # Register voiceprint after audio upload
        doctor.vp_key = "vp/doctor-abc123/voiceprint.wav"
        doctor.vp_text = "请朗读以下内容进行声纹注册..."
        doctor.touch()

        # Check if voiceprint is registered
        if doctor.has_voiceprint:
            print(f"Doctor {doctor.name} voiceprint registered")
        ```
    """

    id: str = StringField(immutable=True, default_factory=lambda: utils.gen_id(prefix="doctor-"))
    username: str = StringField()
    password_hash: str = StringField()
    name: str = StringField()
    employee_number: str | None = StringField(nullable=True)
    department: str | None = StringField(nullable=True)
    hospital_name: str | None = StringField(nullable=True)
    vp_key: str | None = StringField(nullable=True)
    vp_text: str | None = StringField(nullable=True)
    is_active: bool = BoolField(default=True)

    @property
    def has_voiceprint(self) -> bool:
        """Check if the doctor has registered their voiceprint.

        Returns:
            True if voiceprint is registered, False otherwise.
        """
        return self.vp_key is not None
