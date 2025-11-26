from __future__ import annotations

import json
import typing as t

from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from audex.filters.generated import doctor_filter
from audex.filters.generated import session_filter
from audex.helper.mixin import LoggingMixin
from audex.lib.server.auth import AuthMiddleware
from audex.lib.server.types import DoctorSessionData
from audex.lib.server.types import ErrorResponse
from audex.lib.server.types import ExportMultipleRequest
from audex.lib.server.types import LoginRequest
from audex.lib.server.types import LoginResponse
from audex.lib.server.types import SessionListResponse
from audex.valueobj.common.auth import Password

if t.TYPE_CHECKING:
    from audex.lib.exporter import Exporter
    from audex.lib.repos.doctor import DoctorRepository


class RequestHandlers(LoggingMixin):
    """HTTP request handlers."""

    __logtag__ = "audex.lib.http.handlers"

    def __init__(
        self,
        templates: Jinja2Templates,
        doctor_repo: DoctorRepository,
        exporter: Exporter,
    ):
        super().__init__()
        self.templates = templates
        self.doctor_repo = doctor_repo
        self.exporter = exporter

    async def login_page(self, request: Request) -> Response:
        """Render login page."""
        return self.templates.TemplateResponse("login.html.j2", {"request": request})

    async def index_page(self, request: Request) -> Response:
        """Render main export page."""
        session_data: DoctorSessionData = request.state.doctor_session
        return self.templates.TemplateResponse(
            "index.html.j2",
            {
                "request": request,
                "doctor_name": session_data["doctor_name"],
            },
        )

    async def api_login(self, request: Request) -> Response:
        """Handle login request."""
        try:
            body = await request.json()
            login_req = t.cast(LoginRequest, body)

            eid = login_req.get("eid")
            password = login_req.get("password")

            if not eid or not password:
                return self._error_response("Missing eid or password", 400)

            # Find doctor
            f = doctor_filter().eid.eq(eid)
            doctor = await self.doctor_repo.first(f.build())

            if not doctor:
                return self._error_response("Invalid credentials", 401)

            if not doctor.is_active:
                return self._error_response("Account inactive", 401)

            # Verify password
            if not doctor.verify_password(Password.parse(password)):
                return self._error_response("Invalid credentials", 401)

            # Create session
            session_data = DoctorSessionData(
                doctor_id=doctor.id,
                eid=doctor.eid,
                doctor_name=doctor.name,
            )

            login_response = LoginResponse(
                success=True,
                doctor_id=doctor.id,
                doctor_name=doctor.name,
            )

            response = Response(
                content=json.dumps(login_response, ensure_ascii=False),
                media_type="application/json",
            )

            # Set cookie
            response.set_cookie(
                key=AuthMiddleware.COOKIE_NAME,
                value=AuthMiddleware.create_session_cookie(session_data),
                max_age=AuthMiddleware.COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
            )

            self.logger.info(f"Doctor {eid} logged in")
            return response

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return self._error_response(str(e), 500)

    async def api_logout(self, _: Request) -> Response:
        """Handle logout request."""
        response = Response(
            content=json.dumps({"success": True}),
            media_type="application/json",
        )
        response.delete_cookie(AuthMiddleware.COOKIE_NAME)
        return response

    async def api_list_sessions(self, request: Request) -> Response:
        """List sessions for current doctor."""
        try:
            session_data: DoctorSessionData = request.state.doctor_session
            doctor_id = session_data["doctor_id"]

            # Get query params
            page = int(request.query_params.get("page", "0"))
            page_size = int(request.query_params.get("page_size", "50"))

            # Build filter
            f = session_filter().doctor_id.eq(doctor_id).created_at.desc()

            # Get sessions
            sessions = await self.exporter.session_repo.list(
                f.build(),
                page_index=page,
                page_size=page_size,
            )

            # Get total count
            total = await self.exporter.session_repo.count(
                session_filter().doctor_id.eq(doctor_id).build()
            )

            # Convert to response
            list_response = SessionListResponse(
                sessions=[self.exporter._session_to_dict(s) for s in sessions],
                total=total,
                page=page,
                page_size=page_size,
            )

            return Response(
                content=json.dumps(list_response, ensure_ascii=False),
                media_type="application/json",
            )

        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}")
            return self._error_response(str(e), 500)

    async def api_export_session(self, request: Request) -> Response:
        """Export single session."""
        try:
            session_data: DoctorSessionData = request.state.doctor_session
            doctor_id = session_data["doctor_id"]
            session_id = request.path_params["session_id"]

            # Verify ownership
            session = await self.exporter.session_repo.read(session_id)
            if not session:
                return self._error_response("Session not found", 404)

            if session.doctor_id != doctor_id:
                return self._error_response("Access denied", 403)

            # Generate ZIP
            zip_data = await self.exporter.export_session_zip(session_id)

            # Generate filename
            filename = f"{session_id}"
            if session.patient_name:
                filename = f"{session.patient_name}_{session_id}"
            filename += ".zip"

            self.logger.info(f"Exported session {session_id} for doctor {doctor_id}")

            return Response(
                content=zip_data,
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        except Exception as e:
            self.logger.error(f"Failed to export session: {e}")
            return self._error_response(str(e), 500)

    async def api_export_multiple(self, request: Request) -> Response:
        """Export multiple sessions."""
        try:
            session_data: DoctorSessionData = request.state.doctor_session
            doctor_id = session_data["doctor_id"]

            body = await request.json()
            export_req = t.cast(ExportMultipleRequest, body)
            session_ids = export_req.get("session_ids", [])

            if not session_ids:
                return self._error_response("No session IDs provided", 400)

            # Verify all sessions belong to doctor
            for session_id in session_ids:
                session = await self.exporter.session_repo.read(session_id)
                if not session or session.doctor_id != doctor_id:
                    return self._error_response(f"Access denied for session {session_id}", 403)

            # Generate ZIP
            zip_data = await self.exporter.export_multiple_sessions_zip(session_ids)

            filename = f"sessions_export_{len(session_ids)}.zip"

            self.logger.info(f"Exported {len(session_ids)} sessions for doctor {doctor_id}")

            return Response(
                content=zip_data,
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        except Exception as e:
            self.logger.error(f"Failed to export multiple sessions: {e}")
            return self._error_response(str(e), 500)

    def _error_response(self, message: str, status_code: int = 500) -> Response:
        """Create error response."""
        error: ErrorResponse = {"error": message, "details": None}
        return Response(
            content=json.dumps(error, ensure_ascii=False),
            status_code=status_code,
            media_type="application/json",
        )
