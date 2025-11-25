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
        app.on_startup(self.lifespan.__aenter__)
        app.on_shutdown(self.lifespan.__aexit__)

    def run(self) -> None:
        from audex.view.pages import dashboard  # noqa: F401
        from audex.view.pages import login  # noqa: F401
        from audex.view.pages import recording  # noqa: F401
        from audex.view.pages import register  # noqa: F401
        from audex.view.pages import sessions  # noqa: F401
        from audex.view.pages import settings  # noqa: F401
        from audex.view.pages import voiceprint  # noqa: F401

        ui.run(
            title=self.config.core.app.app_name,
            native=self.config.core.app.native,
            language="zh-CN",
            reload=self.config.core.app.debug,
        )
