from __future__ import annotations

import asyncio
import pathlib

from pydantic import Field

from audex.cli.args import BaseArgs
from audex.cli.exceptions import IllegalOperationError
from audex.cli.exceptions import InvalidArgumentError
from audex.cli.helper import display
from audex.config import Config
from audex.config import build_config
from audex.config import setconfig


class Args(BaseArgs):
    config: pathlib.Path = Field(
        ...,
        alias="c",
        description="Path to the configuration file.",
    )

    name: str | None = Field(
        default=None,
        alias="n",
        description="Name of the VPR group to create.",
    )

    def run(self) -> None:
        display.banner("VPR Initialization", subtitle="Initialize Voice Print Recognition Group")

        # Load configuration
        with display.section("Loading Configuration"):
            if self.config:
                display.info(f"Loading config from: {self.config}")

                if self.config.suffix in {".yaml", ".yml"}:
                    setconfig(Config.from_yaml(self.config))
                else:
                    raise InvalidArgumentError(
                        arg="config",
                        value=self.config,
                        reason="Unsupported config file format: "
                        f"{self.config.suffix}.  Supported formats are . yaml, .yml, "
                        f".json, . jsonc, .json5",
                    )
                display.success("Configuration loaded successfully")
            else:
                display.info("Using default configuration")

        cfg = build_config()

        # Show VPR provider info
        with display.section("VPR Provider Information"):
            provider_info: dict[str, str] = {
                "Provider": str(cfg.provider.vpr.provider),
                "Group Name": self.name or "(auto-generated)",
            }

            if cfg.provider.vpr.provider == "xfyun":
                provider_info["Group ID Path"] = str(cfg.provider.vpr.xfyun.group_id_path)
            elif cfg.provider.vpr.provider == "unisound":
                provider_info["Group ID Path"] = str(cfg.provider.vpr.unisound.group_id_path)

            display.key_value(provider_info)

        # Confirm before proceeding
        if not display.confirm("Proceed with VPR group creation?", default=True):
            display.warning("Operation cancelled by user")
            return

        # Initialize infrastructure
        from audex.lib.injectors.container import InfrastructureContainer

        display.step("Initializing VPR infrastructure", step=1)
        infra_container = InfrastructureContainer(config=cfg)
        vpr = infra_container.vpr()

        # Create VPR group
        async def create_group(name: str | None) -> str:
            from audex.lib.vpr import GroupAlreadyExistsError

            async with vpr:
                try:
                    return await vpr.create_group(name)
                except GroupAlreadyExistsError as e:
                    raise IllegalOperationError(operation="Create VPR Group", reason=str(e)) from e

        with display.loading("Creating VPR group..."):
            group_id = asyncio.run(create_group(self.name))

        display.success(f"VPR group created successfully: {group_id}")

        # Save group ID to file
        display.step("Saving group ID to file", step=2)

        group_id_path: pathlib.Path | None = None

        if cfg.provider.vpr.provider == "xfyun":
            group_id_path = pathlib.Path(cfg.provider.vpr.xfyun.group_id_path)
        elif cfg.provider.vpr.provider == "unisound":
            group_id_path = pathlib.Path(cfg.provider.vpr.unisound.group_id_path)

        if group_id_path:
            with display.loading(f"Writing to {group_id_path}... "):
                group_id_path.parent.mkdir(parents=True, exist_ok=True)
                group_id_path.write_text(group_id)

            display.success(f"Group ID saved to: {group_id_path}")
            display.path(group_id_path, label="File", exists=group_id_path.exists())

        # Summary
        print()
        display.header("Initialization Summary")
        summary_data = {
            "Provider": cfg.provider.vpr.provider,
            "Group ID": group_id,
            "Group Name": self.name or "(auto-generated)",
            "Saved To": str(group_id_path) if group_id_path else "N/A",
        }
        display.key_value(summary_data)

        print()
        display.success("VPR initialization completed successfully!  🎉")
