from __future__ import annotations

import os
import pathlib
import typing as t

from pydantic import Field

from audex.cli.args import BaseArgs
from audex.cli.helper import display
from audex.utils import flatten_dict


class Args(BaseArgs):
    format: t.Literal["dotenv", "yaml", "json", "system"] = Field(
        default="dotenv",
        alias="f",
        description="The format of the generated configuration file.",
    )

    output: pathlib.Path | None = Field(
        default=None,
        alias="o",
        description="The output file path.If not provided, the configuration will be printed to stdout.",
    )

    platform: t.Literal["linux", "windows"] | None = Field(
        default=None,
        alias="p",
        description="Target platform for system configuration (only used with --format=system).",
    )

    def run(self) -> None:
        from audex.config import Config

        display.banner("Configuration Generator", subtitle="Generate Configuration File")

        # Show format selection
        with display.section("Generation Options"):
            options_info = {
                "Format": self.format.upper(),
                "Output": str(self.output) if self.output else "(auto-generated filename)",
            }
            if self.format == "system":
                options_info["Platform"] = self.platform or "(current platform)"  # type: ignore
            display.key_value(options_info)

        # Load default configuration
        display.step("Loading default configuration", step=1)
        cfg = Config()

        # For system format, show platform-specific preview
        platform = self.platform or ("linux" if os.name == "posix" else "windows")  # type: ignore
        if self.format == "system":
            with display.section(f"System Configuration Preview ({platform})"):
                display.info(f"Generating system configuration for {platform.upper()}")
                display.warning("Only fields with platform-specific defaults will be included")
                display.info("Unset fields will be omitted from the output")
        else:
            # Preview configuration
            with display.section("Default Configuration Preview"):
                cfg_dict = flatten_dict(cfg.model_dump())
                display.info(f"Total {len(cfg_dict)} configuration keys")
                display.table_dict(cfg_dict)

        # Confirm generation
        if not display.confirm("Generate configuration file?", default=True):
            display.warning("Operation cancelled by user")
            return

        # Generate configuration file
        display.step("Generating configuration file", step=2)

        out = self.output

        with display.loading(f"Writing {self.format.upper()} configuration..."):
            if self.format == "dotenv":
                cfg.to_dotenv(out or (out := pathlib.Path(".env.gen")))
            elif self.format == "yaml":
                cfg.to_yaml(out or (out := pathlib.Path(".config.gen.yml")))
            elif self.format == "json":
                cfg.to_json(out or (out := pathlib.Path(".config.gen.jsonc")))
            elif self.format == "system":
                platform = self.platform or ("linux" if os.name == "posix" else "windows")
                default_filename = f"config.system.{platform}.yml"
                cfg.to_system_yaml(
                    out or (out := pathlib.Path(default_filename)),
                    platform=platform,  # type: ignore
                )

        # Show result
        print()
        display.success("Configuration file generated successfully!")

        # Summary
        display.header("Generation Summary")
        summary_data: dict[str, t.Any] = {
            "Format": self.format.upper(),
            "Output File": str(out),
        }

        if self.format == "system":
            summary_data["Platform"] = platform.upper()
            summary_data["Note"] = "Only non-Unset fields included"
        else:
            summary_data["Total Keys"] = len(cfg_dict)

        display.key_value(summary_data)

        # Show file path with existence check
        display.path(out, label="Saved to", exists=out.exists())

        # Show usage hints
        if self.format == "system":
            print()
            display.header("Usage Instructions")
            display.info("This system configuration file is intended for:")
            print("  • Deployment to /etc/audex/config.system.yml on Linux")
            print("  • Use as read-only system-wide defaults")
            print("  • User configurations should override this at ~/.config/audex/config.yml")

            if platform == "linux":
                print()
                display.info("To deploy on Linux:")
                print(f"  sudo cp {out} /etc/audex/config.system.yml")
                print("  sudo chown root:root /etc/audex/config.system.yml")
                print("  sudo chmod 644 /etc/audex/config.system.yml")

        print()
        display.success("Done!  🎉")
