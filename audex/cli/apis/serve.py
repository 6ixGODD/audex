from __future__ import annotations

import asyncio
import contextlib
import pathlib
import signal
import typing as t

from pydantic import Field

from audex.cli.args import BaseArgs
from audex.cli.exceptions import InvalidArgumentError
from audex.cli.helper import display
from audex.config import Config
from audex.config import build_config
from audex.config import setconfig


class Args(BaseArgs):
    config: pathlib.Path | None = Field(
        default=None,
        alias="c",
        description="Path to the configuration file.",
    )

    host: str = Field(
        default="0. 0.0.0",
        description="Host address to bind the server.",
    )

    port: int = Field(
        default=8000,
        description="Port number to bind the server.",
    )

    def run(self) -> None:
        display.banner("Audex Export Server", subtitle="HTTP Export Service for Session Data")

        # Load configuration
        with display.section("Loading Configuration"):
            if self.config:
                display.info(f"Loading config from: {self.config}")
                display.path(self.config, exists=self.config.exists())

                if self.config.suffix in {".yaml", ".yml"}:
                    setconfig(Config.from_yaml(self.config))
                    display.success("YAML configuration loaded")
                else:
                    raise InvalidArgumentError(
                        arg="config",
                        value=self.config,
                        reason="Unsupported config file format: "
                        f"{self.config.suffix}.  Supported formats are .yaml, . yml, "
                        f". json, .jsonc, .json5",
                    )
            else:
                display.info("Using default configuration")

        # Show server configuration
        with display.section("Server Configuration"):
            server_info = {
                "Host": self.host,
                "Port": self.port,
                "URL": f"http://{self.host}:{self.port}",
            }
            display.key_value(server_info)

        # Initialize infrastructure
        display.step("Initializing infrastructure", step=1)
        cfg = build_config()

        with display.loading("Setting up database and server...  "):
            from audex.lib.injectors.container import InfrastructureContainer

            infra_container = InfrastructureContainer(config=cfg)
            sqlite = infra_container.sqlite()
            server = infra_container.server()

        display.success("Infrastructure initialized")

        # Show available endpoints
        display.step("Starting HTTP server", step=2)
        with display.section("Available Endpoints"):
            endpoints = [
                "GET  /login - Login page",
                "GET  / - Index page",
                "POST /api/login - Authenticate",
                "POST /api/logout - Logout",
                "GET  /api/sessions - List all sessions",
                "GET  /api/sessions/{id}/export - Export single session",
                "POST /api/sessions/export-multiple - Export multiple sessions",
                "GET  /static/* - Static files",
            ]
            display.list_items(endpoints, bullet="→")

        print()
        display.info(f"Server will be available at: http://{self.host}:{self.port}")
        display.info("Press Ctrl+C to stop")

        # Separator before server logs
        print()
        display.separator()
        print()

        # Context manager for server lifecycle
        @contextlib.asynccontextmanager
        async def serve() -> t.AsyncGenerator[asyncio.Task[None], None]:
            async with sqlite:
                display.info("Database connection established")
                # Start server in background task
                server_task = asyncio.create_task(server.start(self.host, self.port))
                try:
                    yield server_task
                finally:
                    await server.close()
                    display.info("Server stopped")

        async def run_server() -> None:
            stop_event = asyncio.Event()

            def set_event(event: asyncio.Event) -> None:
                event.set()

            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, set_event, stop_event)
            loop.add_signal_handler(signal.SIGTERM, set_event, stop_event)

            async with serve() as server_task:
                # Wait for either stop signal or server to finish
                await asyncio.wait(
                    [asyncio.create_task(stop_event.wait()), server_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

        try:
            asyncio.run(run_server())
        except KeyboardInterrupt:
            display.warning("Received interrupt signal")
        finally:
            print()
            display.success("Export server stopped gracefully")
