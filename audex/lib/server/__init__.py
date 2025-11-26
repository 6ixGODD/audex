from __future__ import annotations

import pathlib
import typing as t

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount
from starlette.routing import Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from audex.helper.mixin import LoggingMixin
from audex.lib.server.auth import AuthMiddleware
from audex.lib.server.handlers import RequestHandlers

if t.TYPE_CHECKING:
    from audex.lib.exporter import Exporter
    from audex.lib.repos.doctor import DoctorRepository


class Server(LoggingMixin):
    __logtag__ = "audex.lib.http"

    def __init__(
        self,
        doctor_repo: DoctorRepository,
        exporter: Exporter,
    ):
        super().__init__()
        self.doctor_repo = doctor_repo
        self.exporter = exporter

        # Get template directory (relative to this file)
        template_dir = pathlib.Path(__file__).parent / "templates"
        self.templates = Jinja2Templates(directory=str(template_dir))

        # Create handlers
        self.handlers = RequestHandlers(
            templates=self.templates,
            doctor_repo=doctor_repo,
            exporter=exporter,
        )

        # Create app
        self.app = self._create_app()
        self.server: t.Any = None

    def _create_app(self) -> Starlette:
        """Create Starlette application."""
        routes = [
            # Pages
            Route("/login", self.handlers.login_page, methods=["GET"]),
            Route("/", self.handlers.index_page, methods=["GET"]),
            # API
            Route("/api/login", self.handlers.api_login, methods=["POST"]),
            Route("/api/logout", self.handlers.api_logout, methods=["POST"]),
            Route("/api/sessions", self.handlers.api_list_sessions, methods=["GET"]),
            Route(
                "/api/sessions/{session_id}/export",
                self.handlers.api_export_session,
                methods=["GET"],
            ),
            Route(
                "/api/sessions/export-multiple",
                self.handlers.api_export_multiple,
                methods=["POST"],
            ),
            # Static files
            Mount(
                "/static",
                StaticFiles(directory=str(pathlib.Path(__file__).parent / "templates" / "static")),
                name="static",
            ),
        ]

        middleware = [
            Middleware(AuthMiddleware, doctor_repo=self.doctor_repo),
        ]

        return Starlette(
            debug=False,
            routes=routes,
            middleware=middleware,
        )

    async def start(self, host: str, port: int) -> None:
        import uvicorn

        self.logger.info(f"Starting HTTP server on {host}:{port}")

        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")

        self.server = uvicorn.Server(config)
        await self.server.serve()

    async def close(self) -> None:
        if self.server:
            self.server.should_exit = True
        self.logger.info("HTTP server stopped")
