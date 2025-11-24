from __future__ import annotations

from audex.entity.doctor import Doctor
from audex.filters.generated import doctor_filter
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.session import SessionManager
from audex.service import BaseService
from audex.service.decorators import require_auth
from audex.service.doctor.types import LoginCommand
from audex.service.doctor.types import RegisterCommand


class DoctorService(BaseService):
    def __init__(self, sm: SessionManager, doctor_repo: DoctorRepository):
        super().__init__(sm=sm)
        self.doctor_repo = doctor_repo

    async def login(self, command: LoginCommand) -> None:
        f = doctor_filter().eid.eq(command.eid)
        doctor = await self.doctor_repo.first(f.build())
        if not doctor or not doctor.verify_password(command.password):
            raise ValueError("Invalid credentials")

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
            raise ValueError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise ValueError("Doctor not found")

        await self.sm.logout()
        if not await self.doctor_repo.delete(doctor.id):
            raise ValueError("Failed to delete doctor account")

    @require_auth
    async def current_doctor(self) -> Doctor:
        session = await self.sm.get_session()
        if not session:
            raise ValueError("No active session")

        doctor = await self.doctor_repo.read(session.doctor_id)
        if not doctor:
            raise ValueError("Doctor not found")

        return doctor
