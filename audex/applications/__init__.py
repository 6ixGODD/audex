from __future__ import annotations

import asyncio
import pathlib
import threading
import typing as t

import webview

from audex.applications.api import AudexAPI
from audex.helper.mixin import LoggingMixin
from audex.lifespan import LifeSpan


class AudexApplication(LoggingMixin):
    __logtag__ = "audex.applications.app"

    def __init__(
        self,
        api: AudexAPI,
        lifespan: LifeSpan,
        *,
        width: int = 1280,
        height: int = 800,
        fullscreen: bool = True,
    ):
        super().__init__()
        self.api = api
        self.lifespan = lifespan
        self.width = width
        self.height = height
        self.fullscreen = fullscreen
        self.window: webview.Window | None = None
        self._lifespan_task: asyncio.Task[t.Any] | None = None

    def run(self) -> None:
        app_root = pathlib.Path(__file__).parent
        html_path = app_root / "templates" / "index.html"

        self.window = webview.create_window(
            title="Audex - 智能语音病历系统",
            url=str(html_path),
            js_api=self.api,
            width=self.width,
            height=self.height,
            resizable=True,
            fullscreen=self.fullscreen,
            min_size=(1024, 768),
            background_color="#FFFFFF",
        )

        lifespan_thread = threading.Thread(
            target=self._run_lifespan,
            daemon=True,
        )
        lifespan_thread.start()

        self.logger.info("Starting Audex application")
        webview.start(debug=False)

    def _run_lifespan(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run():
            async with self.lifespan:
                while True:
                    await asyncio.sleep(1)

        try:
            loop.run_until_complete(run())
        except Exception as e:
            self.logger.error(f"Lifespan error: {e}", exc_info=True)
        finally:
            loop.close()
