from __future__ import annotations

from audex import utils
from audex.entity import BaseEntity
from audex.entity import touch_after
from audex.entity.fields import BoolField
from audex.entity.fields import StringBackedField
from audex.entity.fields import StringField
from audex.valueobj.common.auth import HashedPassword
from audex.valueobj.common.auth import Password
from audex.valueobj.common.email import Email
from audex.valueobj.common.phone import CNPhone


class Doctor(BaseEntity):
    """Doctor entity representing a registered doctor account.

    Represents a doctor who can log in, register voiceprint, create sessions,
    and record conversations. This entity serves as the primary user identity
    for the clinic voice recording system.

    Attributes:
        id: The unique identifier of the doctor. Auto-generated with "doctor-"
            prefix for clear categorization.
        eid: Employee/staff ID in the hospital system.
        password_hash: The hashed password for secure authentication.
        name: The doctor's real name for display and records.
        department: Department or specialty. Optional.
        title: Professional title (e.g., "主治医师", "副主任医师"). Optional.
        hospital: Hospital or clinic name. Optional.
        phone: Contact phone number. Optional.
        email: Contact email address. Optional.
        is_active: Indicates whether the doctor account is active. Boolean flag
            controlling login ability, defaults to True.

    Inherited Attributes:
        created_at: Timestamp when the doctor account was created.
        updated_at: Timestamp when the doctor account was last updated.

    Example:
        ```python
        # Create new doctor
        doctor = Doctor(
            eid="EMP001",
            password_hash="hashed_password_here",
            name="张医生",
            department="内科",
            title="主治医师",
            hospital="XX市人民医院",
            phone="13800138000",
            email="zhang@hospital.com",
            is_active=True,
        )

        # Activate/deactivate account
        doctor.deactivate()
        doctor.activate()
        ```
    """

    id: str = StringField(immutable=True, default_factory=lambda: utils.gen_id(prefix="doctor-"))
    eid: str = StringField()
    password_hash: HashedPassword = StringBackedField(HashedPassword)
    name: str = StringField()
    department: str | None = StringField(nullable=True)
    title: str | None = StringField(nullable=True)
    hospital: str | None = StringField(nullable=True)
    phone: CNPhone | None = StringField(nullable=True)
    email: Email | None = StringBackedField(Email, nullable=True)
    is_active: bool = BoolField(default=True)

    @property
    def is_authenticated(self) -> bool:
        """Check if the doctor is authenticated and can access the
        system.

        Returns:
            True if the doctor is active, False otherwise.
        """
        return self.is_active

    @touch_after
    def activate(self) -> None:
        """Activate the doctor account by setting is_active to True.

        Note:
            The updated_at timestamp is automatically updated.
        """
        self.is_active = True

    @touch_after
    def deactivate(self) -> None:
        """Deactivate the doctor account by setting is_active to False.

        Note:
            The updated_at timestamp is automatically updated.
        """
        self.is_active = False

    def verify_password(self, password: Password) -> bool:
        """Verify a password against the doctor's stored password hash.

        Args:
            password: The plain text password to verify.

        Returns:
            True if the password matches the stored hash, False otherwise.
        """
        return self.password_hash == password
