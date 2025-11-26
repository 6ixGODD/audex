from __future__ import annotations

import pathlib

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from pydantic import Field

from audex.cli.args import BaseArgs
from audex.cli.exceptions import InvalidArgumentError
from audex.cli.helper import display
from audex.config import Config
from audex.config import build_config
from audex.config import setconfig
from audex.container import Container
from audex.view import View


class Args(BaseArgs):
    config: pathlib.Path | None = Field(
        default=None,
        alias="c",
        description="Path to the configuration file.",
    )

    def run(self) -> None:
        display.banner("Audex", subtitle="Smart Medical Recording & Transcription System")

        # Load configuration
        with display.section("Loading Configuration"):
            if self.config:
                display.info(f"Loading config from: {self.config}")
                display.path(self.config, exists=self.config.exists())

                if self.config.suffix in {".yaml", ".yml"}:
                    setconfig(Config.from_yaml(self.config))
                    display.success("YAML configuration loaded")
                elif self.config.suffix in {".json", ".jsonc", ".json5"}:
                    setconfig(Config.from_json(self.config))
                    display.success("JSON configuration loaded")
                else:
                    raise InvalidArgumentError(
                        arg="config",
                        value=self.config,
                        reason="Unsupported config file format: "
                        f"{self.config.suffix}. Supported formats are .yaml, .yml, "
                        f".json, .jsonc, . json5",
                    )
            else:
                display.info("Using default configuration")

        # Show configuration summary
        cfg = build_config()
        with display.section("Application Configuration"):
            config_info = {
                "App Name": cfg.app.name,
                "Version": cfg.app.version,
                "Mode": "Native GUI" if cfg.app.native else "Web Browser",
                "Debug": "Enabled" if cfg.app.debug else "Disabled",
                "VPR Provider": cfg.provider.vpr.provider,
                "Transcription": cfg.provider.transcription.provider,
            }
            display.key_value(config_info)

        # Initialize container
        display.step("Initializing application", step=1)
        with display.loading("Wiring dependencies... "):
            container = Container()

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
            import audex.view.pages.voiceprint.update

            container.wire(
                modules=[
                    __name__,
                    audex.view.pages.dashboard,
                    audex.view.pages.login,
                    audex.view.pages.recording,
                    audex.view.pages.register,
                    audex.view.pages.sessions,
                    audex.view.pages.sessions.details,
                    audex.view.pages.sessions.export,
                    audex.view.pages.settings,
                    audex.view.pages.voiceprint,
                    audex.view.pages.voiceprint.enroll,
                    audex.view.pages.voiceprint.update,
                ]
            )

        display.success("Application initialized")

        # Launch info
        display.step("Launching application", step=2)
        print()

        if cfg.app.native:
            display.info("Launching in native window mode")
        else:
            display.info(f"Starting web server on http://{cfg.app.host}:{cfg.app.port}")
            display.info("Application will open in your default browser")

        display.info("Press Ctrl+C to stop")

        # Separator before app logs
        print()
        display.separator(70)
        print()

        # Start application
        run()


@inject
def run(view: View = Provide[Container.views.view]) -> None:
    view.run()
