from __future__ import annotations

import base64
import json
import typing as t

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.responses import Response

from audex.helper.mixin import LoggingMixin
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.server.types import DoctorSessionData

if t.TYPE_CHECKING:
    from starlette.types import ASGIApp


class AuthMiddleware(BaseHTTPMiddleware, LoggingMixin):
    """Authentication middleware using cookie-based sessions."""

    __logtag__ = "audex.lib.http.auth"

    COOKIE_NAME: t.ClassVar[str] = "audex_session"
    COOKIE_MAX_AGE: t.ClassVar[int] = 86400 * 7  # 7 days

    # Public routes that don't require auth
    PUBLIC_ROUTES: t.ClassVar[set[str]] = {"/login", "/api/login", "/static"}

    def __init__(self, app: ASGIApp, doctor_repo: DoctorRepository):
        super().__init__(app)
        self.doctor_repo = doctor_repo

    async def dispatch(
        self, request: Request, call_next: t.Callable[[Request], t.Awaitable[Response]]
    ) -> Response:
        """Process request with authentication check."""
        # Check if route is public
        if self._is_public_route(request.url.path):
            return await call_next(request)

        # Get session from cookie
        session_data = self._get_session_from_cookie(request)

        if not session_data:
            # Not authenticated, redirect to login
            if request.url.path.startswith("/api/"):
                return Response(
                    content=json.dumps({"error": "Unauthorized"}),
                    status_code=401,
                    media_type="application/json",
                )
            return RedirectResponse(url="/login", status_code=303)

        # Verify doctor still exists and is active
        doctor = await self.doctor_repo.read(session_data["doctor_id"])
        if not doctor or not doctor.is_active:
            # Session invalid, clear cookie
            response = RedirectResponse(url="/login", status_code=303)
            response.delete_cookie(self.COOKIE_NAME)
            return response

        # Attach session data to request state
        request.state.doctor_session = session_data

        return await call_next(request)

    def _is_public_route(self, path: str) -> bool:
        """Check if route is public."""
        return any(path.startswith(public) for public in self.PUBLIC_ROUTES)

    def _get_session_from_cookie(self, request: Request) -> DoctorSessionData | None:
        """Extract and decode session from cookie."""
        cookie_value = request.cookies.get(self.COOKIE_NAME)
        if not cookie_value:
            return None

        try:
            # Decode base64
            decoded = base64.b64decode(cookie_value).decode("utf-8")
            session_dict = json.loads(decoded)

            # Validate required fields
            if not all(k in session_dict for k in ["doctor_id", "eid", "doctor_name"]):
                return None

            return t.cast(DoctorSessionData, session_dict)

        except Exception as e:
            self.logger.warning(f"Failed to decode session cookie: {e}")
            return None

    @staticmethod
    def create_session_cookie(session_data: DoctorSessionData) -> str:
        """Create encoded session cookie value."""
        json_str = json.dumps(session_data)
        return base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
