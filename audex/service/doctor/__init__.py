from __future__ import annotations

import typing as t

from audex.entity.doctor import Doctor
from audex.entity.vp import VP
from audex.exceptions import NoActiveSessionError
from audex.filters.generated import doctor_filter
from audex.filters.generated import vp_filter
from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin
from audex.lib.recorder import AudioRecorder
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.vp import VPRepository
from audex.lib.session import SessionManager
from audex.lib.vpr import VPR
from audex.lib.vpr import VPRError
from audex.service import BaseService
from audex.service.decorators import require_auth
from audex.service.doctor.const import ErrorMessages
from audex.service.doctor.const import InvalidCredentialReasons
from audex.service.doctor.exceptions import DoctorNotFoundError
from audex.service.doctor.exceptions import DoctorServiceError
from audex.service.doctor.exceptions import DuplicateEIDError
from audex.service.doctor.exceptions import InternalDoctorServiceError
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
        session_manager: SessionManager,
        config: DoctorServiceConfig,
        doctor_repo: DoctorRepository,
        vp_repo: VPRepository,
        vpr: VPR,
        recorder: AudioRecorder,
    ):
        super().__init__(session_manager=session_manager)
        self.config = config
        self.doctor_repo = doctor_repo
        self.vp_repo = vp_repo
        self.vpr = vpr
        self.recorder = recorder

    async def login(self, command: LoginCommand) -> None:
        """Login a doctor with credentials.

        Args:
            command: Login command with eid and password.

        Raises:
            InvalidCredentialsError: If credentials are invalid.
        """
        try:
            f = doctor_filter().eid.eq(command.eid)
            doctor = await self.doctor_repo.first(f.build())

            if not doctor:
                raise InvalidCredentialsError(
                    ErrorMessages.ACCOUNT_NOT_FOUND,
                    reason=InvalidCredentialReasons.DOCTOR_NOT_FOUND,
                )

            if not doctor.is_active:
                raise InvalidCredentialsError(
                    ErrorMessages.ACCOUNT_INACTIVE,
                    reason=InvalidCredentialReasons.ACCOUNT_INACTIVE,
                )

            if not doctor.verify_password(command.password):
                raise InvalidCredentialsError(
                    ErrorMessages.INVALID_PASSWORD,
                    reason=InvalidCredentialReasons.INVALID_PASSWORD,
                )

            await self.session_manager.login(
                doctor_id=doctor.id,
                eid=doctor.eid,
                doctor_name=doctor.name,
            )

            self.logger.info(f"Doctor {doctor.eid} logged in successfully")

        except InvalidCredentialsError:
            raise
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            raise InternalDoctorServiceError() from e

    async def is_logged_in(self) -> bool:
        """Check if there is an active session."""
        try:
            session = await self.session_manager.get_session()
            return session is not None
        except Exception as e:
            self.logger.error(f"Failed to check login status: {e}")
            return False

    @require_auth
    async def logout(self) -> None:
        """Logout the current doctor."""
        try:
            if not await self.session_manager.logout():
                self.logger.warning("Logout called but no active session")
            else:
                self.logger.info("Doctor logged out successfully")
        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
            raise InternalDoctorServiceError() from e

    async def register(self, command: RegisterCommand) -> Doctor:
        """Register a new doctor account.

        Args:
            command: Registration command with doctor information.

        Returns:
            The created Doctor entity.

        Raises:
            DuplicateEIDError: If EID already exists.
            InternalDoctorServiceError: For internal errors.
        """
        try:
            # Check if EID already exists
            f = doctor_filter().eid.eq(command.eid)
            existing = await self.doctor_repo.first(f.build())
            if existing:
                raise DuplicateEIDError(ErrorMessages.DUPLICATE_EID, eid=command.eid)

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
            await self.session_manager.login(
                doctor_id=uid,
                eid=doctor.eid,
                doctor_name=doctor.name,
            )

            self.logger.info(f"Registered new doctor {doctor.eid}")
            return doctor

        except DuplicateEIDError:
            raise
        except Exception as e:
            self.logger.error(f"Registration failed: {e}")
            raise InternalDoctorServiceError(ErrorMessages.REGISTRATION_FAILED) from e

    @require_auth
    async def delete_account(self) -> None:
        """Delete the current doctor's account and all associated
        data."""
        try:
            session = await self.session_manager.get_session()
            if not session:
                raise NoActiveSessionError(ErrorMessages.NO_ACTIVE_SESSION)

            doctor = await self.doctor_repo.read(session.doctor_id)
            if not doctor:
                raise DoctorNotFoundError(
                    ErrorMessages.DOCTOR_NOT_FOUND,
                    doctor_id=session.doctor_id,
                )

            # Delete all voiceprint registrations
            f = vp_filter().doctor_id.eq(doctor.id)
            await self.vp_repo.delete_many(f.build())

            # Logout first
            await self.session_manager.logout()

            # Delete doctor account
            if not await self.doctor_repo.delete(doctor.id):
                raise DoctorServiceError(ErrorMessages.DOCTOR_DELETE_FAILED)

            self.logger.info(f"Deleted doctor account {doctor.eid}")

        except (NoActiveSessionError, DoctorNotFoundError, DoctorServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to delete account: {e}")
            raise InternalDoctorServiceError() from e

    @require_auth
    async def current_doctor(self) -> Doctor:
        """Get the current logged-in doctor.

        Returns:
            The current Doctor entity.

        Raises:
            NoActiveSessionError: If no active session.
            DoctorNotFoundError: If doctor not found.
        """
        try:
            session = await self.session_manager.get_session()
            if not session:
                raise NoActiveSessionError(ErrorMessages.NO_ACTIVE_SESSION)

            doctor = await self.doctor_repo.read(session.doctor_id)
            if not doctor:
                raise DoctorNotFoundError(
                    ErrorMessages.DOCTOR_NOT_FOUND,
                    doctor_id=session.doctor_id,
                )

            return doctor

        except (NoActiveSessionError, DoctorNotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to get current doctor: {e}")
            raise InternalDoctorServiceError() from e

    @require_auth
    async def enroll_vp(self) -> VPEnrollmentContext:
        """Start voiceprint enrollment for current doctor."""
        try:
            session = await self.session_manager.get_session()
            if not session:
                raise NoActiveSessionError(ErrorMessages.NO_ACTIVE_SESSION)

            doctor = await self.doctor_repo.read(session.doctor_id)
            if not doctor:
                raise DoctorNotFoundError(
                    ErrorMessages.DOCTOR_NOT_FOUND,
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

        except (NoActiveSessionError, DoctorNotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to start VP enrollment: {e}")
            raise InternalDoctorServiceError() from e

    @require_auth
    async def update_vp(self) -> VPUpdateContext:
        """Start voiceprint update for current doctor."""
        try:
            session = await self.session_manager.get_session()
            if not session:
                raise NoActiveSessionError(ErrorMessages.NO_ACTIVE_SESSION)

            doctor = await self.doctor_repo.read(session.doctor_id)
            if not doctor:
                raise DoctorNotFoundError(
                    ErrorMessages.DOCTOR_NOT_FOUND,
                    doctor_id=session.doctor_id,
                )

            # Get active voiceprint
            f = vp_filter().doctor_id.eq(doctor.id).is_active.eq(True)
            vp = await self.vp_repo.first(f.build())

            if not vp:
                raise VoiceprintNotFoundError(
                    ErrorMessages.VOICEPRINT_NOT_FOUND,
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

        except (NoActiveSessionError, DoctorNotFoundError, VoiceprintNotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to start VP update: {e}")
            raise InternalDoctorServiceError() from e

    @require_auth
    async def get_active_vp(self) -> VP | None:
        """Get the active voiceprint for current doctor."""
        try:
            session = await self.session_manager.get_session()
            if not session:
                raise NoActiveSessionError(ErrorMessages.NO_ACTIVE_SESSION)

            doctor = await self.doctor_repo.read(session.doctor_id)
            if not doctor:
                raise DoctorNotFoundError(
                    ErrorMessages.DOCTOR_NOT_FOUND,
                    doctor_id=session.doctor_id,
                )

            f = vp_filter().doctor_id.eq(doctor.id).is_active.eq(True)
            return await self.vp_repo.first(f.build())

        except (NoActiveSessionError, DoctorNotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to get active VP: {e}")
            raise InternalDoctorServiceError() from e

    @require_auth
    async def has_voiceprint(self) -> bool:
        """Check if current doctor has an active voiceprint."""
        try:
            vp = await self.get_active_vp()
            return vp is not None
        except NoActiveSessionError:
            raise
        except DoctorNotFoundError:
            raise
        except Exception:
            return False

    @require_auth
    async def deactivate_vp(self) -> None:
        """Deactivate the current doctor's voiceprint."""
        try:
            session = await self.session_manager.get_session()
            if not session:
                raise NoActiveSessionError(ErrorMessages.NO_ACTIVE_SESSION)

            doctor = await self.doctor_repo.read(session.doctor_id)
            if not doctor:
                raise DoctorNotFoundError(
                    ErrorMessages.DOCTOR_NOT_FOUND,
                    doctor_id=session.doctor_id,
                )

            f = vp_filter().doctor_id.eq(doctor.id).is_active.eq(True)
            vp = await self.vp_repo.first(f.build())

            if not vp:
                raise VoiceprintNotFoundError(
                    ErrorMessages.VOICEPRINT_NOT_FOUND,
                    doctor_id=doctor.id,
                )

            vp.is_active = False
            await self.vp_repo.update(vp)

            self.logger.info(f"Deactivated voiceprint for doctor {doctor.eid}")

        except (NoActiveSessionError, DoctorNotFoundError, VoiceprintNotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to deactivate VP: {e}")
            raise InternalDoctorServiceError() from e

    @require_auth
    async def update(self, command: UpdateCommand) -> Doctor:
        """Update current doctor's profile information."""
        try:
            session = await self.session_manager.get_session()
            if not session:
                raise NoActiveSessionError(ErrorMessages.NO_ACTIVE_SESSION)

            doctor = await self.doctor_repo.read(session.doctor_id)
            if not doctor:
                raise DoctorNotFoundError(
                    ErrorMessages.DOCTOR_NOT_FOUND,
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

        except (NoActiveSessionError, DoctorNotFoundError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to update profile: {e}")
            raise InternalDoctorServiceError() from e

    @require_auth
    async def change_password(
        self,
        old_password: Password,
        new_password: Password,
    ) -> None:
        """Change the current doctor's password."""
        try:
            session = await self.session_manager.get_session()
            if not session:
                raise NoActiveSessionError(ErrorMessages.NO_ACTIVE_SESSION)

            doctor = await self.doctor_repo.read(session.doctor_id)
            if not doctor:
                raise DoctorNotFoundError(
                    ErrorMessages.DOCTOR_NOT_FOUND,
                    doctor_id=session.doctor_id,
                )

            if not doctor.verify_password(old_password):
                raise InvalidCredentialsError(
                    ErrorMessages.OLD_PASSWORD_INCORRECT,
                    reason=InvalidCredentialReasons.INVALID_PASSWORD,
                )

            doctor.password_hash = new_password.hash()
            doctor.touch()
            await self.doctor_repo.update(doctor)

            self.logger.info(f"Changed password for doctor {doctor.eid}")

        except (NoActiveSessionError, DoctorNotFoundError, InvalidCredentialsError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to change password: {e}")
            raise InternalDoctorServiceError() from e


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
        try:
            await self.recorder.start("voiceprints", self.doctor.id, "enrollment")
            self.logger.info(f"Started VP enrollment for doctor {self.doctor.eid}")
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            raise InternalDoctorServiceError(ErrorMessages.VOICEPRINT_ENROLL_FAILED) from e

    async def close(self) -> VPEnrollResult:
        """Finish recording and complete enrollment."""
        try:
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
            try:
                vpr_uid = await self.vpr.enroll(data=audio_data, sr=self.sample_rate, uid=None)
                self.logger.info(f"Enrolled with VPR, uid: {vpr_uid}")
            except VPRError as e:
                self.logger.error(f"VPR enrollment failed: {e}")
                raise InternalDoctorServiceError(ErrorMessages.VOICEPRINT_ENROLL_FAILED) from e

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

        except InternalDoctorServiceError:
            raise
        except Exception as e:
            self.logger.error(f"VP enrollment failed: {e}")
            raise InternalDoctorServiceError(ErrorMessages.VOICEPRINT_ENROLL_FAILED) from e


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
        try:
            await self.recorder.start("voiceprints", self.doctor.id, "update")
            self.logger.info(f"Started VP update for doctor {self.doctor.eid}")
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            raise InternalDoctorServiceError(ErrorMessages.VOICEPRINT_UPDATE_FAILED) from e

    async def close(self) -> VPEnrollResult:
        """Finish recording and complete update."""
        try:
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
            try:
                await self.vpr.update(uid=self.vp.vpr_uid, data=audio_data, sr=self.sample_rate)
                self.logger.info(f"Updated VPR uid: {self.vp.vpr_uid}")
            except VPRError as e:
                self.logger.error(f"VPR update failed: {e}")
                raise InternalDoctorServiceError(ErrorMessages.VOICEPRINT_UPDATE_FAILED) from e

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

        except InternalDoctorServiceError:
            raise
        except Exception as e:
            self.logger.error(f"VP update failed: {e}")
            raise InternalDoctorServiceError(ErrorMessages.VOICEPRINT_UPDATE_FAILED) from e
