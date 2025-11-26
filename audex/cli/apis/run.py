from __future__ import annotations

import os
import pathlib
import platform

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
from audex.utils import flatten_dict
from audex.view import View


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
                row_spacing=1,  # 添加行间距
            )

        # Setup native environment if needed
        if cfg.core.app.native:
            display.step("Setting up native environment", step=1)
            with display.section("Environment Configuration"):
                _setup_native_environment(cfg)

        # Initialize container
        display.step("Initializing application", step=2 if cfg.core.app.native else 1)
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
        display.step("Launching application", step=3 if cfg.core.app.native else 2)
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


def _setup_native_environment(cfg: Config) -> None:
    """Setup environment variables for native Qt application.

    Args:
        cfg: Application configuration
    """
    import PyQt6.QtCore

    system = platform.system()
    env_vars = {}

    # === PyQt6 Plugin Path ===
    try:
        plugins_path = PyQt6.QtCore.QLibraryInfo.path(
            PyQt6.QtCore.QLibraryInfo.LibraryPath.PluginsPath
        )
        env_vars["QT_PLUGIN_PATH"] = plugins_path
        display.info(f"Qt plugins path: {plugins_path}")
    except Exception as e:
        display.warning(f"Could not set Qt plugin path: {e}")

    # === PyWebView GUI Backend ===
    env_vars["PYWEBVIEW_GUI"] = "qt6"
    display.info("PyWebView backend: qt6")

    # === Platform-Specific Settings ===
    if system == "Linux":
        _setup_linux_env(cfg, env_vars)
    elif system == "Windows":
        _setup_windows_env(cfg, env_vars)
    elif system == "Darwin":  # macOS
        _setup_macos_env(cfg, env_vars)
    else:
        display.warning(f"Unsupported platform: {system}")

    # === Apply Environment Variables ===
    for key, value in env_vars.items():
        os.environ[key] = value
        display.debug(f"Set {key}={value}")

    display.success("Native environment configured")


def _setup_linux_env(cfg: Config, env_vars: dict[str, str]) -> None:
    """Setup Linux-specific environment variables.

    Args:
        cfg: Application configuration
        env_vars: Dictionary to store environment variables
    """
    display.info("Configuring for Linux")

    # === QT Platform Plugin ===
    # TODO: Try different platform plugins in order of preference
    # platform_plugins = ["xcb", "wayland", "offscreen"]

    # Check if specific platform is available
    qt_qpa_platform = os.environ.get("QT_QPA_PLATFORM")
    if qt_qpa_platform:
        display.info(f"Using existing QT_QPA_PLATFORM: {qt_qpa_platform}")
    else:
        # Detect if running under Wayland
        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        xdg_session_type = os.environ.get("XDG_SESSION_TYPE")

        if wayland_display or xdg_session_type == "wayland":
            env_vars["QT_QPA_PLATFORM"] = "wayland;xcb"  # Fallback to xcb
            display.info("Detected Wayland session, using wayland with xcb fallback")
        else:
            env_vars["QT_QPA_PLATFORM"] = "xcb"
            display.info("Using X11 (xcb) platform")

    # === Touch Support ===
    if hasattr(cfg.core.app, "touch") and cfg.core.app.touch:
        env_vars["QT_ENABLE_TOUCH_EVENTS"] = "1"
        display.info("Touch events enabled")

    # === High DPI Support ===
    if not os.environ.get("QT_AUTO_SCREEN_SCALE_FACTOR"):
        env_vars["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        display.debug("Auto screen scaling enabled")

    # === OpenGL Settings ===
    # Force software rendering if needed
    if os.environ.get("LIBGL_ALWAYS_SOFTWARE") == "1":
        display.warning("Software rendering mode detected")

    # Set OpenGL to desktop for better compatibility
    if not os.environ.get("QT_XCB_GL_INTEGRATION"):
        env_vars["QT_XCB_GL_INTEGRATION"] = "xcb_egl"
        display.debug("OpenGL integration: xcb_egl")

    # === Accessibility ===
    # Disable accessibility bridge if causing issues
    # env_vars["QT_LINUX_ACCESSIBILITY_ALWAYS_ON"] = "0"

    # === Font Rendering ===
    if not os.environ.get("QT_SCALE_FACTOR"):
        # Let system handle DPI
        pass


def _setup_windows_env(cfg: Config, env_vars: dict[str, str]) -> None:
    """Setup Windows-specific environment variables.

    Args:
        cfg: Application configuration
        env_vars: Dictionary to store environment variables
    """
    display.info("Configuring for Windows")

    # === QT Platform Plugin ===
    env_vars["QT_QPA_PLATFORM"] = "windows"
    display.info("Using Windows platform plugin")

    # === High DPI Support ===
    if not os.environ.get("QT_AUTO_SCREEN_SCALE_FACTOR"):
        env_vars["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        env_vars["QT_ENABLE_HIGHDPI_SCALING"] = "1"
        display.debug("High DPI scaling enabled")

    # === DirectX vs OpenGL ===
    # Windows defaults to ANGLE (DirectX), but can force OpenGL
    if not os.environ.get("QT_OPENGL"):
        env_vars["QT_OPENGL"] = "angle"  # or "desktop" or "software"
        display.debug("OpenGL backend: ANGLE (DirectX)")

    # === Touch Support ===
    if hasattr(cfg.core.app, "touch") and cfg.core.app.touch:
        env_vars["QT_ENABLE_TOUCH_EVENTS"] = "1"
        display.info("Touch events enabled")

    # === Media Foundation ===
    # Enable Windows Media Foundation for multimedia
    if not os.environ.get("QT_MULTIMEDIA_PREFERRED_PLUGINS"):
        env_vars["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"
        display.debug("Multimedia backend: Windows Media Foundation")


def _setup_macos_env(_: Config, env_vars: dict[str, str]) -> None:
    """Setup macOS-specific environment variables.

    Args:
        cfg: Application configuration
        env_vars: Dictionary to store environment variables
    """
    display.info("Configuring for macOS")

    # === QT Platform Plugin ===
    env_vars["QT_QPA_PLATFORM"] = "cocoa"
    display.info("Using Cocoa platform plugin")

    # === High DPI Support ===
    if not os.environ.get("QT_AUTO_SCREEN_SCALE_FACTOR"):
        env_vars["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        display.debug("High DPI scaling enabled")

    # === Metal vs OpenGL ===
    # macOS prefers Metal on newer systems
    if not os.environ.get("QSG_RHI_BACKEND"):
        # metal, opengl, or software
        env_vars["QSG_RHI_BACKEND"] = "metal"
        display.debug("Rendering backend: Metal")

    # === Multimedia ===
    if not os.environ.get("QT_MULTIMEDIA_PREFERRED_PLUGINS"):
        env_vars["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "darwin"
        display.debug("Multimedia backend: AVFoundation")

    # === Menu Bar ===
    # Keep menu in window instead of system menu bar
    # env_vars["QT_MAC_WANTS_LAYER"] = "1"


@inject
def run(view: View = Provide[Container.views.view]) -> None:
    view.run()
