from __future__ import annotations

import pathlib

from fastapi import Response
from nicegui import app
from nicegui import ui

from audex.config import Config
from audex.helper.mixin import LoggingMixin
from audex.lifespan import LifeSpan

app.add_static_files("/static", str(pathlib.Path(__file__).parent / "static"))


@app.get("/sw.js")
async def service_worker() -> Response:
    return Response(content="// Empty service worker", media_type="application/javascript")


class View(LoggingMixin):
    __logtag__ = "audex.view"

    def __init__(
        self,
        lifespan: LifeSpan,
        config: Config,
    ):
        super().__init__()
        self.lifespan = lifespan
        self.config = config
        app.on_startup(self.lifespan.startup)
        app.on_shutdown(self.lifespan.shutdown)

    def run(self) -> None:
        import audex.view.pages.dashboard
        import audex.view.pages.login
        import audex.view.pages.recording
        import audex.view.pages.register
        import audex.view.pages.sessions
        import audex.view.pages.sessions.details
        import audex.view.pages.sessions.export
        import audex.view.pages.settings
        import audex.view.pages.voiceprint
        import audex.view.pages.voiceprint.enroll
        import audex.view.pages.voiceprint.update  # noqa: F401

        ui.run(
            title=self.config.core.app.app_name,
            native=self.config.core.app.native,
            language="zh-CN",
            reload=self.config.core.app.debug,
            fullscreen=self.config.core.app.fullscreen,
            tailwind=False,
        )
