from __future__ import annotations

import asyncio
import typing as t

from audex.entity.session import Session
from audex.helper.mixin import LoggingMixin
from audex.lib.session import SessionManager
from audex.service.doctor import DoctorService
from audex.service.doctor.types import LoginCommand
from audex.service.doctor.types import RegisterCommand
from audex.service.session import SessionService
from audex.service.session.types import CreateSessionCommand
from audex.valueobj.common.auth import Password


class AudexAPI(LoggingMixin):
    __logtag__ = "audex.applications.api"

    def __init__(
        self,
        session_manager: SessionManager,
        doctor_service: DoctorService,
        session_service: SessionService,
    ):
        super().__init__()
        self.session_manager = session_manager
        self.doctor_service = doctor_service
        self.session_service = session_service
        self._active_recordings: dict[str, t.Any] = {}

    def _run_async(self, coro: t.Coroutine[t.Any, t.Any, t.Any]) -> t.Any:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def check_login_status(self) -> dict[str, t.Any]:
        try:
            is_logged_in = self._run_async(self.session_manager.is_logged_in())

            if is_logged_in:
                session = self._run_async(self.session_manager.get_session())
                return {
                    "logged_in": True,
                    "session": session.to_dict() if session else None,
                }
            return {"logged_in": False, "session": None}
        except Exception as e:
            self.logger.error(f"Error checking login status: {e}", exc_info=True)
            return {"logged_in": False, "session": None}

    def login(self, eid: str, password: str) -> dict[str, t.Any]:
        try:
            command = LoginCommand(eid=eid, password=Password.parse(password))
            self._run_async(self.doctor_service.login(command))

            session = self._run_async(self.session_manager.get_session())

            return {
                "success": True,
                "session": session.to_dict() if session else None,
            }
        except Exception as e:
            self.logger.error(f"Login error: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
            }

    def register(
        self,
        eid: str,
        password: str,
        name: str,
        department: str | None = None,
        title: str | None = None,
        hospital: str | None = None,
    ) -> dict[str, t.Any]:
        try:
            command = RegisterCommand(
                eid=eid,
                password=Password.parse(password),
                name=name,
                department=department,
                title=title,
                hospital=hospital,
            )
            doctor = self._run_async(self.doctor_service.register(command))

            return {
                "success": True,
                "message": "注册成功",
                "doctor": {
                    "id": doctor.id,
                    "eid": doctor.eid,
                    "name": doctor.name,
                },
            }
        except Exception as e:
            self.logger.error(f"Register error: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
            }

    def logout(self) -> dict[str, t.Any]:
        try:
            self._run_async(self.doctor_service.logout())
            return {"success": True}
        except Exception as e:
            self.logger.error(f"Logout error: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
            }

    def get_sessions(
        self,
        page_index: int = 0,
        page_size: int = 20,
    ) -> dict[str, t.Any]:
        try:
            session = self._run_async(self.session_manager.get_session())
            if not session:
                return {"success": False, "message": "未登录"}

            sessions = self._run_async(
                self.session_service.list(
                    doctor_id=session.doctor_id,
                    page_index=page_index,
                    page_size=page_size,
                )
            )

            return {
                "success": True,
                "sessions": [self._session_to_dict(s) for s in sessions],
            }
        except Exception as e:
            self.logger.error(f"Error getting sessions: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    def create_session(
        self,
        patient_name: str | None = None,
        clinic_number: str | None = None,
        medical_record_number: str | None = None,
        diagnosis: str | None = None,
        notes: str | None = None,
    ) -> dict[str, t.Any]:
        try:
            session = self._run_async(self.session_manager.get_session())
            if not session:
                return {"success": False, "message": "未登录"}

            command = CreateSessionCommand(
                doctor_id=session.doctor_id,
                patient_name=patient_name,
                clinic_number=clinic_number,
                medical_record_number=medical_record_number,
                diagnosis=diagnosis,
                notes=notes,
            )

            new_session = self._run_async(self.session_service.create(command))

            return {
                "success": True,
                "session": self._session_to_dict(new_session),
            }
        except Exception as e:
            self.logger.error(f"Error creating session: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    def delete_session(self, session_id: str) -> dict[str, t.Any]:
        try:
            self._run_async(self.session_service.delete(session_id))
            return {"success": True}
        except Exception as e:
            self.logger.error(f"Error deleting session: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    def get_utterances(self, session_id: str) -> dict[str, t.Any]:
        try:
            utterances = self._run_async(self.session_service.get_utterances(session_id))

            return {
                "success": True,
                "utterances": [
                    {
                        "id": u.id,
                        "text": u.text,
                        "speaker": u.speaker.value,
                        "confidence": u.confidence,
                        "start_time_ms": u.start_time_ms,
                        "end_time_ms": u.end_time_ms,
                        "sequence": u.sequence,
                    }
                    for u in utterances
                ],
            }
        except Exception as e:
            self.logger.error(f"Error getting utterances: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    def start_recording(self, session_id: str) -> dict[str, t.Any]:
        try:
            if session_id in self._active_recordings:
                return {"success": False, "message": "会话已在录音中"}

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def setup_recording():
                ctx = await self.session_service.session(session_id)
                await ctx.start()
                return ctx

            ctx = loop.run_until_complete(setup_recording())
            self._active_recordings[session_id] = {"context": ctx, "loop": loop}

            return {"success": True, "recording": True}
        except Exception as e:
            self.logger.error(f"Error starting recording: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    def stop_recording(self, session_id: str) -> dict[str, t.Any]:
        try:
            if session_id not in self._active_recordings:
                return {"success": False, "message": "会话未在录音"}

            recording = self._active_recordings.pop(session_id)
            ctx = recording["context"]
            loop = recording["loop"]

            loop.run_until_complete(ctx.close())
            loop.close()

            return {"success": True}
        except Exception as e:
            self.logger.error(f"Error stopping recording: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    def get_app_info(self) -> dict[str, str]:
        return {
            "name": "Audex",
            "version": "0.1.0",
            "description": "智能语音病历系统",
        }

    @staticmethod
    def _session_to_dict(session: Session) -> dict[str, t.Any]:
        return {
            "id": session.id,
            "patient_name": session.patient_name,
            "clinic_number": session.clinic_number,
            "medical_record_number": session.medical_record_number,
            "diagnosis": session.diagnosis,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "notes": session.notes,
        }
