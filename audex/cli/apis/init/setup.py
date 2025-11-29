from __future__ import annotations

import asyncio
import getpass
import pathlib

from pydantic import Field

from audex.cli.args import BaseArgs
from audex.cli.exceptions import InvalidArgumentError
from audex.cli.helper import display
from audex.config import Config
from audex.utils import Unset


class Args(BaseArgs):
    config: pathlib.Path = Field(
        ...,
        alias="c",
        description="Path to the input configuration file.",
    )

    output: pathlib.Path = Field(
        ...,
        alias="o",
        description="Path to save the configured file.",
    )

    def run(self) -> None:
        display.banner("Audex Setup Wizard", subtitle="Interactive Configuration Setup")

        # Load input configuration
        with display.section("Loading Configuration"):
            if not self.config.exists():
                raise InvalidArgumentError(
                    arg="config",
                    value=str(self.config),
                    reason=f"Configuration file not found: {self.config}",
                )

            display.info(f"Loading from: {self.config}")

            if self.config.suffix in {".yaml", ".yml"}:
                cfg = Config.from_yaml(self.config)
            elif self.config.suffix in {".json", ".jsonc", ".json5"}:
                cfg = Config.from_json(self.config)
            else:
                raise InvalidArgumentError(
                    arg="config",
                    value=str(self.config),
                    reason=f"Unsupported config format: {self.config.suffix}",
                )

            display.success("Configuration loaded successfully")

        # Configure Transcription Provider
        cfg = self._config_transcription(cfg)

        # Configure VPR Provider
        cfg = self._config_vpr(cfg)

        # Save configuration
        with display.section("Saving Configuration"):
            display.info(f"Output: {self.output}")

            if self.output.exists():
                if display.confirm(f"File already exists.Overwrite {self.output}?", default=False):
                    import datetime

                    backup_path = self.output.with_suffix(
                        f".backup.{datetime.datetime.now():%Y%m%d_%H%M%S}.yml"
                    )
                    display.info(f"Backing up to: {backup_path}")
                    self.output.rename(backup_path)
                else:
                    display.warning("Operation cancelled")
                    return

            self.output.parent.mkdir(parents=True, exist_ok=True)

            with display.loading("Writing configuration..."):
                cfg.to_yaml(self.output)

            display.success("Configuration saved successfully")
            display.path(self.output, label="Saved to", exists=self.output.exists())

        # Initialize VPR Group
        if display.confirm("Initialize VPR Group now?", default=True):
            self._init_vpr_group(cfg, self.output)

        # Show summary
        self._show_summary(cfg, self.output)

    def _config_transcription(self, cfg: Config) -> Config:
        """Configure transcription provider."""
        with display.section("Transcription Provider Configuration"):
            current_provider = cfg.provider.transcription.provider
            display.info(f"Current provider: {current_provider}")

            # Check if Dashscope API key is set
            dashscope_key = cfg.provider.transcription.dashscope.credential.api_key
            is_unset = dashscope_key in ("<UNSET>", None, "") or isinstance(dashscope_key, Unset)

            if is_unset:
                display.warning("Dashscope API Key is NOT configured")
                api_key = self._prompt_secret("Enter Dashscope API Key")
                cfg.provider.transcription.dashscope.credential.api_key = api_key
                display.success("Dashscope API Key updated")
            else:
                display.success("Dashscope API Key is configured")
                display.info(f"Current key: {self._mask_secret(str(dashscope_key))}")
                if display.confirm("Update Dashscope API Key?", default=False):
                    api_key = self._prompt_secret("Enter new Dashscope API Key")
                    cfg.provider.transcription.dashscope.credential.api_key = api_key
                    display.success("Dashscope API Key updated")

        return cfg

    def _config_vpr(self, cfg: Config) -> Config:
        """Configure VPR provider."""
        with display.section("VPR Provider Configuration"):
            current_provider = cfg.provider.vpr.provider
            display.info(f"Current provider: {current_provider}")

            # Ask if user wants to change provider
            if not display.confirm(f"Keep VPR provider as '{current_provider}'?", default=True):
                print("\nAvailable VPR Providers:")
                print("  1) xfyun")
                print("  2) unisound")

                choice = input("\nSelect provider [1]: ").strip() or "1"

                if choice == "1":
                    selected_provider = "xfyun"
                elif choice == "2":
                    selected_provider = "unisound"
                else:
                    display.warning("Invalid choice, keeping current provider")
                    selected_provider = current_provider

                cfg.provider.vpr.provider = selected_provider  # type: ignore
                display.success(f"VPR provider set to: {selected_provider}")
            else:
                selected_provider = current_provider

            # Configure credentials for selected provider
            if selected_provider == "xfyun":
                cfg = self._config_xfyun(cfg)
            elif selected_provider == "unisound":
                cfg = self._config_unisound(cfg)

        return cfg

    def _config_xfyun(self, cfg: Config) -> Config:
        """Configure XFYun credentials."""
        print("\n--- XFYun Configuration ---")

        xfyun_cfg = cfg.provider.vpr.xfyun.credential

        # App ID
        current_app_id = xfyun_cfg.app_id
        is_unset = current_app_id in ("<UNSET>", None, "")

        if is_unset:
            display.warning("XFYun App ID is NOT configured")
            app_id = input("Enter XFYun App ID: ").strip()
            cfg.provider.vpr.xfyun.credential.app_id = app_id
            display.success("XFYun App ID updated")
        else:
            display.info(f"Current App ID: {current_app_id}")
            if display.confirm("Update XFYun App ID?", default=False):
                app_id = input("Enter XFYun App ID: ").strip()
                cfg.provider.vpr.xfyun.credential.app_id = app_id
                display.success("XFYun App ID updated")

        # API Key
        current_api_key = xfyun_cfg.api_key
        is_unset = current_api_key in ("<UNSET>", None, "")

        if is_unset:
            display.warning("XFYun API Key is NOT configured")
            api_key = self._prompt_secret("Enter XFYun API Key")
            cfg.provider.vpr.xfyun.credential.api_key = api_key
            display.success("XFYun API Key updated")
        else:
            display.info(f"Current API Key: {self._mask_secret(current_api_key)}")
            if display.confirm("Update XFYun API Key?", default=False):
                api_key = self._prompt_secret("Enter XFYun API Key")
                cfg.provider.vpr.xfyun.credential.api_key = api_key
                display.success("XFYun API Key updated")

        # API Secret
        current_secret = xfyun_cfg.api_secret
        is_unset = current_secret in ("<UNSET>", None, "")

        if is_unset:
            display.warning("XFYun API Secret is NOT configured")
            api_secret = self._prompt_secret("Enter XFYun API Secret")
            cfg.provider.vpr.xfyun.credential.api_secret = api_secret
            display.success("XFYun API Secret updated")
        else:
            display.info(f"Current API Secret: {self._mask_secret(current_secret)}")
            if display.confirm("Update XFYun API Secret?", default=False):
                api_secret = self._prompt_secret("Enter XFYun API Secret")
                cfg.provider.vpr.xfyun.credential.api_secret = api_secret
                display.success("XFYun API Secret updated")

        return cfg

    def _config_unisound(self, cfg: Config) -> Config:
        """Configure Unisound credentials."""
        print("\n--- Unisound Configuration ---")

        unisound_cfg = cfg.provider.vpr.unisound.credential

        # AppKey
        current_appkey = unisound_cfg.appkey
        is_unset = current_appkey in ("<UNSET>", None, "")

        if is_unset:
            display.warning("Unisound AppKey is NOT configured")
            appkey = input("Enter Unisound AppKey: ").strip()
            cfg.provider.vpr.unisound.credential.appkey = appkey
            display.success("Unisound AppKey updated")
        else:
            display.info(f"Current AppKey: {current_appkey}")
            if display.confirm("Update Unisound AppKey?", default=False):
                appkey = input("Enter Unisound AppKey: ").strip()
                cfg.provider.vpr.unisound.credential.appkey = appkey
                display.success("Unisound AppKey updated")

        # Secret
        current_secret = unisound_cfg.secret
        is_unset = current_secret in ("<UNSET>", None, "")

        if is_unset:
            display.warning("Unisound Secret is NOT configured")
            secret = self._prompt_secret("Enter Unisound Secret")
            cfg.provider.vpr.unisound.credential.secret = secret
            display.success("Unisound Secret updated")
        else:
            display.info(f"Current Secret: {self._mask_secret(current_secret)}")
            if display.confirm("Update Unisound Secret?", default=False):
                secret = self._prompt_secret("Enter Unisound Secret")
                cfg.provider.vpr.unisound.credential.secret = secret
                display.success("Unisound Secret updated")

        return cfg

    def _init_vpr_group(self, cfg: Config, config_path: pathlib.Path) -> None:
        """Initialize VPR group."""
        display.step("Initializing VPR Group", step=1)

        from audex.lib.injectors.container import InfrastructureContainer

        infra_container = InfrastructureContainer(config=cfg)
        vpr = infra_container.vpr()

        async def create_group() -> str:
            from audex.lib.vpr import GroupAlreadyExistsError

            async with vpr:
                try:
                    return await vpr.create_group(None)
                except GroupAlreadyExistsError:
                    display.warning("VPR Group already exists, skipping creation")
                    # Try to read existing group ID
                    if cfg.provider.vpr.provider == "xfyun":
                        gid_path = pathlib.Path(cfg.provider.vpr.xfyun.group_id_path)
                    else:
                        gid_path = pathlib.Path(cfg.provider.vpr.unisound.group_id_path)

                    if gid_path.exists():
                        return gid_path.read_text().strip()
                    raise

        try:
            with display.loading("Creating VPR group..."):
                group_id = asyncio.run(create_group())

            display.success(f"VPR Group ID: {group_id}")

            # Save group ID
            if cfg.provider.vpr.provider == "xfyun":
                gid_path = pathlib.Path(cfg.provider.vpr.xfyun.group_id_path)
            else:
                gid_path = pathlib.Path(cfg.provider.vpr.unisound.group_id_path)

            gid_path.parent.mkdir(parents=True, exist_ok=True)
            gid_path.write_text(group_id)

            display.success(f"Group ID saved to: {gid_path}")

        except Exception as e:
            display.warning(f"Failed to initialize VPR group: {e}")
            display.info("You can manually initialize later with:")
            display.info(f"  python3 -m audex init vprgroup --config {config_path}")

    def _show_summary(self, cfg: Config, output_path: pathlib.Path) -> None:
        """Show configuration summary."""
        print()
        display.header("Setup Summary")

        summary_data = {
            "Config File": str(output_path),
            "Transcription Provider": cfg.provider.transcription.provider,
            "VPR Provider": cfg.provider.vpr.provider,
        }

        display.key_value(summary_data)

        print()
        display.success("Setup completed successfully!  🎉")
        print()
        display.info("Next steps:")
        print("  • Run Audex: audex")
        print(f"  • Edit config: {output_path}")
        print()

    @staticmethod
    def _prompt_secret(prompt: str) -> str:
        """Prompt for secret input (hidden)."""
        return getpass.getpass(f"{prompt}: ")

    @staticmethod
    def _mask_secret(secret: str) -> str:
        """Mask a secret for display."""
        if not secret or len(secret) < 8:
            return "***"
        return f"{secret[:4]}...{secret[-4:]}"
