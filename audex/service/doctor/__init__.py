from __future__ import annotations

from audex.entity.doctor import Doctor
from audex.filters.generated import doctor_filter
from audex.lib.audio import AudioRecorder
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.vp import VPRepository
from audex.lib.session import SessionManager
from audex.service import BaseService
from audex.service.decorators import require_auth
from audex.service.doctor.const import InvalidCredentialReasons
from audex.service.doctor.exceptions import DoctorNotFoundError
from audex.service.doctor.exceptions import DoctorServiceError
from audex.service.doctor.exceptions import InvalidCredentialsError
from audex.service.doctor.types import LoginCommand
from audex.service.doctor.types import RegisterCommand
from audex.service.doctor.types import UpdateCommand
from audex.valueobj.common.auth import Password


class DoctorService(BaseService):
    def __init__(
        self,
        sm: SessionManager,
        doctor_repo: DoctorRepository,
        vp_repo: VPRepository,
        recorder: AudioRecorder,
    ):
        super().__init__(sm=sm)
        self.doctor_repo = doctor_repo
        self.vp_repo = vp_repo
        self.recorder = recorder

    async def login(self, command: LoginCommand) -> None:
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

        await self.sm.login(doctor_id=doctor.id, eid=doctor.eid, doctor_name=doctor.name)

    @require_auth
    async def logout(self) -> None:
        if not await self.sm.logout():
            raise ValueError("No active session to logout")

    async def register(self, command: RegisterCommand) -> Doctor:
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
        await self.sm.login(doctor_id=uid, eid=doctor.eid, doctor_name=doctor.name)
        return doctor

    @require_auth
    async def delete_account(self) -> None:
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError("Doctor not found", doctor_id=session.doctor_id)

        await self.sm.logout()
        if not await self.doctor_repo.delete(doctor.id):
            raise DoctorServiceError("Failed to delete doctor account")

    @require_auth
    async def current_doctor(self) -> Doctor:
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError("Doctor not found", doctor_id=session.doctor_id)

        return doctor

    @require_auth
    async def enroll_vp(self): ...

    @require_auth
    async def update_vp(self): ...

    @require_auth
    async def update(self, command: UpdateCommand) -> Doctor:
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError("Doctor not found", doctor_id=session.doctor_id)

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

        if not await self.doctor_repo.update(doctor):
            raise DoctorServiceError("Failed to update doctor information")

        return doctor

    @require_auth
    async def change_password(self, old_password: Password, new_password: Password) -> None:
        session = await self.sm.get_session()
        if not session:
            raise DoctorServiceError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise DoctorNotFoundError("Doctor not found", doctor_id=session.doctor_id)

        if not doctor.verify_password(old_password):
            raise InvalidCredentialsError(
                "Old password is incorrect",
                reason=InvalidCredentialReasons.INVALID_PASSWORD,
            )

        doctor.password_hash = new_password.hash()
        if not await self.doctor_repo.update(doctor):
            raise DoctorServiceError("Failed to change password")
