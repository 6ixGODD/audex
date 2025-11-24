from __future__ import annotations

import typing as t

from audex.entity.doctor import Doctor
from audex.entity.vp import VP
from audex.filters.generated import doctor_filter
from audex.filters.generated import vp_filter
from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin
from audex.lib.recorder import AudioRecorder
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.vp import VPRepository
from audex.lib.session import SessionManager
from audex.lib.vpr import VPR
from audex.service import BaseService
from audex.service.decorators import require_auth
from audex.service.doctor.const import InvalidCredentialReasons
from audex.service.doctor.exceptions import DoctorNotFoundError
from audex.service.doctor.exceptions import DoctorServiceError
from audex.service.doctor.exceptions import InvalidCredentialsError
from audex.service.doctor.exceptions import VoiceprintNotFoundError
from audex.service.doctor.types import LoginCommand
from audex.service.doctor.types import RegisterCommand
from audex.service.doctor.types import UpdateCommand
from audex.service.doctor.types import VPEnrollResult
from audex.types import AbstractSession
from audex.valueobj.common.auth import Password


class DoctorServiceConfig(t.NamedTuple):
    """DoctorService configuration.

    Attributes:
        vpr_sr: Sample rate for VPR verification.
        vpr_text_content: Text content for VPR enrollment.
    """

    vpr_sr: int = 16000
    vpr_text_content: str = "请朗读: 您好，我是一名医生，我将为您提供专业的医疗服务。"


class DoctorService(BaseService):
    """Service for managing doctor accounts and voiceprint
    operations."""

    __logtag__ = "audex.service.doctor"

    def __init__(
        self,
        sm: SessionManager,
        config: DoctorServiceConfig,
        doctor_repo: DoctorRepository,
        vp_repo: VPRepository,
        vpr: VPR,
        recorder: AudioRecorder,
    ):
        super().__init__(sm=sm)
        self.config = config
        self.doctor_repo = doctor_repo
        self.vp_repo = vp_repo
        self.vpr = vpr
        self.recorder = recorder

    async def login(self, command: LoginCommand) -> None:
        """Login a doctor by employee ID and password."""
        f = doctor_filter().eid.eq(command.eid)
        doctor = await self.doctor_repo.first(f.build())
        if not doctor:
            raise InvalidCredentialsError(
                "Invalid credentials",
                reason=InvalidCredentialReasons.DOCTOR_NOT_FOUND,
            )
        if not doctor.verify_password(command.password):
            raise InvalidCredentialsError(
                "Invalid credentials",
                reason=InvalidCredentialReasons.INVALID_PASSWORD,
            )

        await self.sm.login(
            doctor_id=doctor.id,
            eid=doctor.eid,
            doctor_name=doctor.name,
        )

        self.logger.info(f"Doctor {doctor.eid} logged in")

    @require_auth
    async def logout(self) -> None:
        """Logout the current doctor."""
        if not await self.sm.logout():
            raise ValueError("No active session to logout")

        self.logger.info("Doctor logged out")

    async def register(self, command: RegisterCommand) -> Doctor:
        """Register a new doctor account."""
        doctor = Doctor(
            eid=command.eid,
            password_hash=command.password.hash(),
            name=command.name,
            department=command.department,
            title=command.title,
            hospital=command.hospital,
            phone=command.phone,
            email=command.email,
            is_active=True,
        )

        uid = await self.doctor_repo.create(doctor)
        doctor.id = uid

        # Auto-login after registration
        await self.sm.login(
            doctor_id=uid,
            eid=doctor.eid,
            doctor_name=doctor.name,
        )

        self.logger.info(f"Registered new doctor {doctor.eid}")
        return doctor

    @require_auth
    async def delete_account(self) -> None:
        """Delete the current doctor's account."""
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError(
                "Doctor not found",
                doctor_id=session.doctor_id,
            )

        # Delete all voiceprint registrations
        f = vp_filter().doctor_id.eq(doctor.id)
        await self.vp_repo.delete_many(f.build())

        # Logout first
        await self.sm.logout()

        # Delete doctor account
        if not await self.doctor_repo.delete(doctor.id):
            raise DoctorServiceError("Failed to delete doctor account")

        self.logger.info(f"Deleted doctor account {doctor.eid}")

    @require_auth
    async def current_doctor(self) -> Doctor:
        """Get the current logged-in doctor."""
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError(
                "Doctor not found",
                doctor_id=session.doctor_id,
            )

        return doctor

    @require_auth
    async def enroll_vp(self) -> VPEnrollmentContext:
        """Start voiceprint enrollment with live recording.

        Returns a container that manages the recording process.

        Returns:
            VPEnrollmentContainer for managing the enrollment process.

        Example:
            ```python
            async with await doctor_service.enroll_vp() as container:
                # Start recording
                await container.start()

                # Recording in progress...
                # User speaks the text_content

                # Finish and submit to VPR
                result = await container.close()
                print(f"Enrolled! VPR UID: {result.vpr_uid}")
            ```
        """
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError(
                "Doctor not found",
                doctor_id=session.doctor_id,
            )

        return VPEnrollmentContext(
            doctor=doctor,
            vp_repo=self.vp_repo,
            recorder=self.recorder,
            vpr=self.vpr,
            text_content=self.config.vpr_text_content,
            sample_rate=self.config.vpr_sr,
            group_id=self.vpr.group_id,
        )

    @require_auth
    async def update_vp(self) -> VPUpdateContext:
        """Start voiceprint update with live recording.

        Returns a container that manages the recording process.

        Returns:
            VPUpdateContainer for managing the update process.

        Example:
            ```python
            async with await doctor_service.update_vp() as container:
                await container.start()

                # Recording...

                result = await container.close()
                print(f"Updated! VPR UID: {result.vpr_uid}")
            ```
        """
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError(
                "Doctor not found",
                doctor_id=session.doctor_id,
            )

        # Get active voiceprint
        f = vp_filter().doctor_id.eq(doctor.id).is_active.eq(True)
        vp = await self.vp_repo.first(f.build())

        if not vp:
            raise VoiceprintNotFoundError(
                "No active voiceprint registration found",
                doctor_id=doctor.id,
            )

        return VPUpdateContext(
            doctor=doctor,
            vp=vp,
            vp_repo=self.vp_repo,
            recorder=self.recorder,
            vpr=self.vpr,
            text_content=self.config.vpr_text_content,
            sample_rate=self.config.vpr_sr,
        )

    @require_auth
    async def get_active_vp(self) -> VP | None:
        """Get the current doctor's active voiceprint."""
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError("Doctor not found", doctor_id=session.doctor_id)

        f = vp_filter().doctor_id.eq(doctor.id).is_active.eq(True)
        return await self.vp_repo.first(f.build())

    @require_auth
    async def has_voiceprint(self) -> bool:
        """Check if the current doctor has an active voiceprint."""
        vp = await self.get_active_vp()
        return vp is not None

    @require_auth
    async def deactivate_vp(self) -> None:
        """Deactivate the current doctor's voiceprint."""
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError(
                "Doctor not found",
                doctor_id=session.doctor_id,
            )

        f = vp_filter().doctor_id.eq(doctor.id).is_active.eq(True)
        vp = await self.vp_repo.first(f.build())

        if not vp:
            raise VoiceprintNotFoundError("No active voiceprint found", doctor_id=doctor.id)

        vp.is_active = False
        await self.vp_repo.update(vp)

        self.logger.info(f"Deactivated voiceprint for doctor {doctor.eid}")

    @require_auth
    async def update(self, command: UpdateCommand) -> Doctor:
        """Update the current doctor's profile information."""
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError(
                "Doctor not found",
                doctor_id=session.doctor_id,
            )

        # Update fields if provided
        if command.name is not None:
            doctor.name = command.name
        if command.department is not None:
            doctor.department = command.department
        if command.title is not None:
            doctor.title = command.title
        if command.hospital is not None:
            doctor.hospital = command.hospital
        if command.phone is not None:
            doctor.phone = command.phone
        if command.email is not None:
            doctor.email = command.email

        doctor.touch()

        await self.doctor_repo.update(doctor)

        self.logger.info(f"Updated profile for doctor {doctor.eid}")
        return doctor

    @require_auth
    async def change_password(
        self,
        old_password: Password,
        new_password: Password,
    ) -> None:
        """Change the current doctor's password."""
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError(
                "Doctor not found",
                doctor_id=session.doctor_id,
            )

        if not doctor.verify_password(old_password):
            raise InvalidCredentialsError(
                "Old password is incorrect",
                reason=InvalidCredentialReasons.INVALID_PASSWORD,
            )

        doctor.password_hash = new_password.hash()
        doctor.touch()

        await self.doctor_repo.update(doctor)

        self.logger.info(f"Changed password for doctor {doctor.eid}")


class VPEnrollmentContext(LoggingMixin, AsyncContextMixin, AbstractSession):
    """Context for managing voiceprint enrollment with live
    recording."""

    __logtag__ = "audex.service.doctor:VPEnrollmentContext"

    def __init__(
        self,
        doctor: Doctor,
        vp_repo: VPRepository,
        recorder: AudioRecorder,
        vpr: VPR,
        text_content: str,
        sample_rate: int,
        group_id: str | None,
    ):
        super().__init__()
        self.doctor = doctor
        self.vp_repo = vp_repo
        self.recorder = recorder
        self.vpr = vpr
        self.text_content = text_content
        self.sample_rate = sample_rate
        self.group_id = group_id

    async def start(self) -> None:
        """Start recording for voiceprint enrollment."""
        await self.recorder.start(
            "voiceprints",
            self.doctor.id,
            "enrollment",
        )
        self.logger.info(f"Started voiceprint enrollment recording for {self.doctor.eid}")

    async def close(self) -> VPEnrollResult:
        """Finish recording and complete enrollment.

        Returns:
            VPEnrollResult with registration details.
        """
        # Stop recording and get audio segment
        segment = await self.recorder.stop()

        # Get audio data for VPR (resample if needed)
        audio_data = await self.recorder.segment(
            started_at=segment.started_at,
            ended_at=segment.ended_at,
            rate=self.sample_rate,
            channels=1,
        )

        # Enroll with VPR
        vpr_uid = await self.vpr.enroll(data=audio_data, sr=self.sample_rate, uid=None)

        self.logger.info(f"Enrolled with VPR, uid: {vpr_uid}")

        # Deactivate existing active VPs
        f = vp_filter().doctor_id.eq(self.doctor.id).is_active.eq(True)
        existing = await self.vp_repo.list(f.build())

        if existing:
            for vp in existing:
                vp.is_active = False
            await self.vp_repo.update_many(existing)
            self.logger.debug(f"Deactivated {len(existing)} existing VP(s)")

        # Create new VP
        vp = VP(
            doctor_id=self.doctor.id,
            vpr_uid=vpr_uid,
            vpr_group_id=self.group_id,
            audio_key=segment.key,
            text_content=self.text_content,
            sample_rate=self.sample_rate,
            is_active=True,
        )

        vp_id = await self.vp_repo.create(vp)

        self.logger.info(f"Created VP {vp_id} for doctor {self.doctor.eid}")
        self.recorder.clear_frames()

        return VPEnrollResult(
            vp_id=vp_id,
            vpr_uid=vpr_uid,
            audio_key=segment.key,
            duration_ms=segment.duration_ms,
        )


class VPUpdateContext(LoggingMixin, AsyncContextMixin, AbstractSession):
    """Context for managing voiceprint update with live recording."""

    __logtag__ = "audex.service.doctor:VPUpdateContext"

    def __init__(
        self,
        doctor: Doctor,
        vp: VP,
        vp_repo: VPRepository,
        recorder: AudioRecorder,
        vpr: VPR,
        text_content: str,
        sample_rate: int,
    ):
        super().__init__()
        self.doctor = doctor
        self.vp = vp
        self.vp_repo = vp_repo
        self.recorder = recorder
        self.vpr = vpr
        self.text_content = text_content
        self.sample_rate = sample_rate

    async def start(self) -> None:
        """Start recording for voiceprint update."""
        await self.recorder.start(
            "voiceprints",
            self.doctor.id,
            "update",
        )
        self.logger.info(f"Started voiceprint update recording for {self.doctor.eid}")

    async def close(self) -> VPEnrollResult:
        """Finish recording and complete update.

        Returns:
            VPEnrollResult with updated details.
        """
        # Stop recording and get audio segment
        segment = await self.recorder.stop()

        # Get audio data for VPR (resample if needed)
        audio_data = await self.recorder.segment(
            started_at=segment.started_at,
            ended_at=segment.ended_at,
            rate=self.sample_rate,
            channels=1,
        )

        # Update VPR
        await self.vpr.update(
            uid=self.vp.vpr_uid,
            data=audio_data,
            sr=self.sample_rate,
        )

        self.logger.info(f"Updated VPR uid: {self.vp.vpr_uid}")

        # Update VP record
        self.vp.audio_key = segment.key
        self.vp.text_content = self.text_content
        self.vp.sample_rate = self.sample_rate
        self.vp.touch()

        await self.vp_repo.update(self.vp)

        self.logger.info(f"Updated VP {self.vp.id} for doctor {self.doctor.eid}")
        self.recorder.clear_frames()

        return VPEnrollResult(
            vp_id=self.vp.id,
            vpr_uid=self.vp.vpr_uid,
            audio_key=segment.key,
            duration_ms=segment.duration_ms,
        )
