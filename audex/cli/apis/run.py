from __future__ import annotations

import pathlib
import platform
import typing as t

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from nicegui import core
from pydantic import Field

from audex.cli.args import BaseArgs
from audex.cli.exceptions import InvalidArgumentError
from audex.cli.helper import display
from audex.config import Config
from audex.config import build_config
from audex.config import setconfig
from audex.utils import flatten_dict

core.app.native.start_args.update({"gui": "qt"})


class Args(BaseArgs):
    config: pathlib.Path | None = Field(
        default=None,
        alias="c",
        description="Path to the configuration file.",
    )

    def run(self) -> None:
        display.banner("Audex", subtitle="Smart Medical Recording & Transcription System")

        # Boostrap
        display.step("Bootstrapping application", step=0)
        print()

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
                        f"{self.config.suffix}.  Supported formats are .yaml, .yml, "
                        f".json, .jsonc, . json5",
                    )
            else:
                display.info("Using default configuration")

        # Show configuration summary
        cfg = build_config()
        with display.section("Application Configuration"):
            display.table_dict(
                flatten_dict(cfg.model_dump()),
                headers=("Config Key", "Value"),
                max_col_width=50,
                row_spacing=1,
            )

        # Initialize container
        display.step("Initializing application", step=1)
        with display.loading("Wiring dependencies... "):
            from audex.container import Container

            container = Container()

            import audex.view.pages

            container.wire(modules=[__name__], packages=[audex.view.pages])

        display.success("Application initialized")

        # Launch info
        display.step("Launching application", step=2)
        print()

        if cfg.core.app.native:
            display.info("Launching in native window mode")
            display.info(f"GUI Backend: PyQt6 ({platform.system()})")
        else:
            display.info("Application will open in your default browser")

        display.info("Press Ctrl+C to stop")

        # Separator before app logs
        print()
        display.separator(70)
        print()

        # Start application
        run()


from audex.container import Container  # noqa: E402

if t.TYPE_CHECKING:
    from audex.view import View  # noqa: E402


@inject
def run(view: View = Provide[Container.views.view]) -> None:
    view.run()
