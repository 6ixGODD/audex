from __future__ import annotations

import typing as t

from audex.entity.doctor import Doctor
from audex.entity.voiceprint_registration import VoiceprintRegistration
from audex.helper.hash import argon2_hash
from audex.helper.hash import argon2_verify
from audex.lib.database.sqlite import SQLite
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.voiceprint_registration import VoiceprintRegistrationRepository
from audex.lib.store import Store
from audex.lib.vpr import VPR
from audex.service import BaseService


class DoctorService(BaseService):
    """Doctor service for authentication and voiceprint management.

    This service handles doctor registration, login, and voiceprint
    registration operations. It integrates with the VPR system for
    voice-based authentication.

    Attributes:
        doctor_repo: Repository for doctor data persistence.
        vpr_repo: Repository for voiceprint registration data.
        vpr: Voice Print Recognition system interface.
        store: Storage system for audio files.
    """

    __logtag__ = "DoctorService"

    def __init__(
        self,
        sqlite: SQLite,
        vpr: VPR,
        store: Store,
    ) -> None:
        """Initialize the doctor service.

        Args:
            sqlite: SQLite database connection.
            vpr: Voice Print Recognition system interface.
            store: Storage system for audio files.
        """
        super().__init__()
        self.doctor_repo = DoctorRepository(sqlite)
        self.vpr_repo = VoiceprintRegistrationRepository(sqlite)
        self.vpr = vpr
        self.store = store

    async def register(
        self,
        username: str,
        password: str,
        name: str,
        employee_number: str | None = None,
        department: str | None = None,
        hospital_name: str | None = None,
    ) -> Doctor:
        """Register a new doctor account.

        Args:
            username: Unique username for the doctor.
            password: Plain text password (will be hashed).
            name: Doctor's real name.
            employee_number: Optional employee number (工号).
            department: Optional department (科室).
            hospital_name: Optional hospital name.

        Returns:
            The newly created doctor entity.

        Raises:
            ValueError: If username already exists.
        """
        self.logger.info(f"Attempting to register doctor with username: {username}")

        # Check if username already exists
        existing_doctor = await self.doctor_repo.read_by_username(username)
        if existing_doctor is not None:
            self.logger.warning(f"Registration failed: username {username} already exists")
            raise ValueError(f"Username '{username}' already exists")

        # Hash the password
        password_hash = argon2_hash(password)

        # Create doctor entity
        doctor = Doctor(
            username=username,
            password_hash=password_hash,
            name=name,
            employee_number=employee_number,
            department=department,
            hospital_name=hospital_name,
            is_active=True,
        )

        # Save to database
        doctor_id = await self.doctor_repo.create(doctor)
        self.logger.info(f"Doctor registered successfully with ID: {doctor_id}")

        return doctor

    async def login(self, username: str, password: str) -> Doctor:
        """Authenticate a doctor and return their account.

        Args:
            username: Doctor's username.
            password: Plain text password to verify.

        Returns:
            The authenticated doctor entity.

        Raises:
            ValueError: If authentication fails (invalid credentials or inactive account).
        """
        self.logger.info(f"Login attempt for username: {username}")

        # Retrieve doctor by username
        doctor = await self.doctor_repo.read_by_username(username)
        if doctor is None:
            self.logger.warning(f"Login failed: username {username} not found")
            raise ValueError("Invalid username or password")

        # Verify password
        if not argon2_verify(password, doctor.password_hash):
            self.logger.warning(f"Login failed: invalid password for username {username}")
            raise ValueError("Invalid username or password")

        # Check if account is active
        if not doctor.is_active:
            self.logger.warning(f"Login failed: account {username} is inactive")
            raise ValueError("Account is inactive")

        self.logger.info(f"Login successful for username: {username}")
        return doctor

    async def register_voiceprint(
        self,
        doctor_id: str,
        audio_data: bytes,
        sample_rate: t.Literal[8000, 16000],
        vp_text: str,
        vpr_group_id: str,
        vpr_system: str,
    ) -> VoiceprintRegistration:
        """Register a doctor's voiceprint with the VPR system.

        This should be called during first-time login or when re-registering
        a voiceprint. It uploads the audio to storage and registers with
        the VPR system.

        Args:
            doctor_id: The ID of the doctor.
            audio_data: The voiceprint audio data (raw bytes).
            sample_rate: Audio sample rate (8000 or 16000 Hz).
            vp_text: The text content read during registration.
            vpr_group_id: The VPR group ID to register in.
            vpr_system: The VPR system type (e.g., "xfyun").

        Returns:
            The voiceprint registration entity.

        Raises:
            ValueError: If doctor not found or VPR registration fails.
        """
        self.logger.info(f"Registering voiceprint for doctor: {doctor_id}")

        # Retrieve doctor
        doctor = await self.doctor_repo.read(doctor_id)
        if doctor is None:
            self.logger.error(f"Voiceprint registration failed: doctor {doctor_id} not found")
            raise ValueError(f"Doctor with ID '{doctor_id}' not found")

        # Upload audio to storage
        audio_key = self.store.key_builder.build("voiceprints", doctor_id, "voiceprint.wav")
        await self.store.upload(audio_data, audio_key)
        self.logger.info(f"Voiceprint audio uploaded to: {audio_key}")

        # Register with VPR system
        try:
            vp_id = await self.vpr.register(audio_data, sample_rate)
            self.logger.info(f"Voiceprint registered with VPR system, vp_id: {vp_id}")
        except Exception as e:
            self.logger.error(f"VPR registration failed: {e}")
            # Clean up uploaded file
            await self.store.delete(audio_key)
            raise ValueError(f"VPR registration failed: {e}")

        # Create voiceprint registration record
        vpr_registration = VoiceprintRegistration(
            doctor_id=doctor_id,
            vp_id=vp_id,
            vpr_group_id=vpr_group_id,
            vpr_system=vpr_system,
            registration_address=str(self.vpr),  # Store VPR system info
        )
        await self.vpr_repo.create(vpr_registration)

        # Update doctor entity with voiceprint info
        doctor.vp_key = audio_key
        doctor.vp_text = vp_text
        doctor.touch()
        await self.doctor_repo.update(doctor)

        self.logger.info(f"Voiceprint registration completed for doctor: {doctor_id}")
        return vpr_registration

    async def has_voiceprint(self, doctor_id: str) -> bool:
        """Check if a doctor has registered their voiceprint.

        Args:
            doctor_id: The ID of the doctor.

        Returns:
            True if voiceprint is registered, False otherwise.
        """
        doctor = await self.doctor_repo.read(doctor_id)
        if doctor is None:
            return False
        return doctor.has_voiceprint

    async def get_voiceprint_registration(
        self, doctor_id: str
    ) -> VoiceprintRegistration | None:
        """Get the voiceprint registration for a doctor.

        Args:
            doctor_id: The ID of the doctor.

        Returns:
            The voiceprint registration if exists, None otherwise.
        """
        return await self.vpr_repo.read_by_doctor_id(doctor_id)
