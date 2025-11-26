from __future__ import annotations

import pathlib
import typing as t

from pydantic import Field

from audex.cli.args import BaseArgs
from audex.cli.helper import display
from audex.utils import flatten_dict


class Args(BaseArgs):
    format: t.Literal["dotenv", "yaml", "json"] = Field(
        default="dotenv",
        alias="f",
        description="The format of the generated configuration file.",
    )

    output: pathlib.Path | None = Field(
        default=None,
        alias="o",
        description="The output file path. If not provided, the configuration will be printed to stdout.",
    )

    def run(self) -> None:
        from audex.config import Config

        display.banner("Configuration Generator", subtitle="Generate Default Configuration File")

        # Show format selection
        with display.section("Generation Options"):
            options_info = {
                "Format": self.format.upper(),
                "Output": str(self.output) if self.output else "(stdout)",
            }
            display.key_value(options_info)

        # Load default configuration
        display.step("Loading default configuration", step=1)
        cfg = Config()

        # Preview configuration
        with display.section("Default Configuration Preview"):
            cfg_dict = flatten_dict(cfg.model_dump())
            display.info(f"Total {len(cfg_dict)} configuration keys")
            display.table_dict(cfg_dict, ("Config Key", "Value"))

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

        # Show result
        print()
        display.success("Configuration file generated successfully!")

        # Summary
        display.header("Generation Summary")
        summary_data = {
            "Format": self.format.upper(),
            "Output File": str(out),
            "Total Keys": len(cfg_dict),
        }
        display.key_value(summary_data)

        # Show file path with existence check
        display.path(out, label="Saved to", exists=out.exists())

        print()
        display.success("Done!  🎉")
