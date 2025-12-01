#!/usr/bin/env python3
"""Build DEB package (supports both Docker and native WSL)."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

# ============================================================================
# Configuration - Auto-detect environment
# ============================================================================

# Check if running in Docker
IS_DOCKER = pathlib.Path("/.dockerenv").exists() or os.environ.get("CONTAINER") == "docker"

# WSL mode flag (will be set by command line argument)
WSL_MODE = False

if IS_DOCKER:
    # Docker environment (default)
    BUILD_DIR = pathlib.Path("/build")
    TEMPLATES_DIR = BUILD_DIR / "templates"
    OUTPUT_DIR = BUILD_DIR / "output"
    VERSION_FILE = BUILD_DIR / "VERSION"
    ICON_SRC = BUILD_DIR / "logo.svg"
else:
    # Will be configured based on WSL_MODE flag
    SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
    BUILD_DIR = None  # Will be set later
    TEMPLATES_DIR = SCRIPT_DIR / "templates"
    VERSION_FILE = SCRIPT_DIR.parent.parent / "VERSION"
    ICON_SRC = SCRIPT_DIR.parent.parent / "audex" / "view" / "static" / "images" / "logo.svg"

PACKAGE_NAME = "audex"


# ============================================================================
# Logging
# ============================================================================


class Colors:
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    NC = "\033[0m"


def log_info(msg: str) -> None:
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.NC}")


def log_success(msg: str) -> None:
    print(f"{Colors.GREEN}✅ {msg}{Colors.NC}")


def log_warn(msg: str) -> None:
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.NC}")


def log_error(msg: str) -> None:
    print(f"{Colors.RED}❌ {msg}{Colors.NC}", file=sys.stderr)


def log_step(msg: str) -> None:
    print(f"\n{Colors.BLUE}━━━ {msg}{Colors.NC}")


# ============================================================================
# Helper Functions
# ============================================================================


def run_command(cmd: list[str], cwd: pathlib.Path | None = None) -> None:
    """Run a command and check for errors."""
    try:
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed: {' '.join(cmd)}")
        if e.stderr:
            log_error(f"Error: {e.stderr}")
        raise


def get_version_from_file() -> str:
    """Read version from VERSION file."""
    if not VERSION_FILE.exists():
        log_error(f"VERSION file not found: {VERSION_FILE}")
        sys.exit(1)

    version = VERSION_FILE.read_text().strip()

    if not version:
        log_error("VERSION file is empty")
        sys.exit(1)

    return version


def normalize_line_endings(content: str) -> str:
    """Convert CRLF to LF."""
    return content.replace("\r\n", "\n").replace("\r", "\n")


# ============================================================================
# Build Steps
# ============================================================================


def resolve_version(version_arg: str | None) -> str:
    """Resolve version to build."""
    if version_arg:
        log_info(f"Using version from argument: {version_arg}")
        return version_arg

    log_info("Reading version from VERSION file...")
    version = get_version_from_file()
    log_info(f"Version: {version}")
    return version


def create_package_structure(pkg_dir: pathlib.Path) -> None:
    """Create DEB package directory structure."""
    log_step("Creating package structure...")

    # Clean old build
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)

    directories = [
        pkg_dir / "DEBIAN",
        pkg_dir / "etc" / "audex" / "templates",
        pkg_dir / "etc" / "audex" / "systemd",
        pkg_dir / "opt" / "audex",
        pkg_dir / "usr" / "bin",
        pkg_dir / "usr" / "share" / "applications",
        pkg_dir / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps",
        pkg_dir / "usr" / "share" / "pixmaps",
        pkg_dir / "usr" / "share" / "doc" / "audex",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    log_success("Package structure created")


def copy_template_files(pkg_dir: pathlib.Path, version: str, arch: str) -> None:
    """Copy and process template files."""
    log_step("Copying template files...")

    # Copy DEBIAN scripts with line ending normalization
    for script in ["postinst", "prerm", "postrm"]:
        src = TEMPLATES_DIR / "DEBIAN" / script
        dst = pkg_dir / "DEBIAN" / script

        if not src.exists():
            log_error(f"Template file not found: {src}")
            sys.exit(1)

        content = src.read_text(encoding="utf-8")
        content = normalize_line_endings(content)
        dst.write_text(content, encoding="utf-8")
        dst.chmod(0o755)

        log_info(f"   Copied {script}")

    # Process control template
    control_template = TEMPLATES_DIR / "DEBIAN" / "control.template"
    control_dst = pkg_dir / "DEBIAN" / "control"

    if not control_template.exists():
        log_error(f"Control template not found: {control_template}")
        sys.exit(1)

    control_content = control_template.read_text(encoding="utf-8")
    control_content = normalize_line_endings(control_content)
    control_content = control_content.replace("{VERSION}", version)
    control_content = control_content.replace("{ARCH}", arch)

    control_dst.write_text(control_content, encoding="utf-8")
    log_info("   Processed control file")

    # Copy launcher scripts
    for script in ["audex", "audex-setup", "audex-enable-service"]:
        src = TEMPLATES_DIR / "usr" / "bin" / script
        dst = pkg_dir / "usr" / "bin" / script

        if not src.exists():
            log_error(f"Launcher script not found: {src}")
            sys.exit(1)

        content = src.read_text(encoding="utf-8")
        content = normalize_line_endings(content)
        dst.write_text(content, encoding="utf-8")
        dst.chmod(0o755)

        log_info(f"   Copied {script}")

    # Copy desktop file
    desktop_src = TEMPLATES_DIR / "usr" / "share" / "applications" / "audex.desktop"
    desktop_dst = pkg_dir / "usr" / "share" / "applications" / "audex.desktop"

    if desktop_src.exists():
        content = desktop_src.read_text(encoding="utf-8")
        content = normalize_line_endings(content)
        desktop_dst.write_text(content, encoding="utf-8")
        desktop_dst.chmod(0o644)
        log_info("   Copied desktop file")
    else:
        log_warn("Desktop file not found, skipping")

    # Copy user systemd service template
    user_service_src = TEMPLATES_DIR / "etc" / "audex" / "systemd" / "audex.service"
    user_service_dst = pkg_dir / "etc" / "audex" / "systemd" / "audex.service"

    if user_service_src.exists():
        content = user_service_src.read_text(encoding="utf-8")
        content = normalize_line_endings(content)
        user_service_dst.write_text(content, encoding="utf-8")
        user_service_dst.chmod(0o644)
        log_info("   Copied user systemd service template")
    else:
        log_warn("User systemd service template not found, skipping")

    log_success("Template files copied")


def copy_icon(pkg_dir: pathlib.Path) -> None:
    """Copy application icon if available."""
    log_step("Copying icon...")

    icon_locations = [
        pkg_dir / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps" / "audex.svg",
        pkg_dir / "usr" / "share" / "pixmaps" / "audex.svg",
    ]

    if ICON_SRC.exists():
        for icon_dst in icon_locations:
            shutil.copy2(ICON_SRC, icon_dst)
            icon_dst.chmod(0o644)
            log_info(f"   Copied icon to {icon_dst.relative_to(pkg_dir)}")
        log_success("Icon copied to all locations")
    else:
        log_warn(f"Icon not found at {ICON_SRC}, creating placeholder")
        placeholder = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
  <circle cx="24" cy="24" r="20" fill="#1976d2"/>
  <text x="24" y="32" font-size="24" fill="white" text-anchor="middle" font-family="sans-serif" font-weight="bold">A</text>
</svg>"""
        for icon_dst in icon_locations:
            icon_dst.write_text(placeholder, encoding="utf-8")
            icon_dst.chmod(0o644)


def build_deb_package(pkg_dir: pathlib.Path, version: str, arch: str) -> pathlib.Path:
    """Build the DEB package."""
    log_step("Building DEB package...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    deb_file = OUTPUT_DIR / f"{PACKAGE_NAME}_{version}_{arch}.deb"

    if deb_file.exists():
        log_info("Removing existing DEB file")
        deb_file.unlink()

    run_command(["dpkg-deb", "--build", str(pkg_dir), str(deb_file)])

    if not deb_file.exists():
        log_error("DEB file was not created")
        sys.exit(1)

    log_success(f"DEB package built: {deb_file.name}")
    return deb_file


def show_summary(deb_file: pathlib.Path, version: str, arch: str) -> None:
    """Show build summary."""
    print("\n" + "=" * 60)
    log_success("Build Complete!")
    print("=" * 60)
    print(f"\n📦 Package: {deb_file.name}")
    print(f"📊 Size: {deb_file.stat().st_size / 1024 / 1024:.2f} MB")

    if IS_DOCKER:
        print(f"📁 Location: /build/output/{deb_file.name}")
    elif WSL_MODE:
        print(f"📁 Location: {deb_file}")
        print(f"📁 Relative: ~/{deb_file.relative_to(pathlib.Path.home())}")
    else:
        print(f"📁 Location: {deb_file}")

    print(f"\n🔖 Version: {version}")
    print(f"🏗️  Architecture: {arch}")

    if IS_DOCKER:
        print("🔧 Environment: Docker")
    elif WSL_MODE:
        print("🔧 Environment: WSL (native)")
    else:
        print("🔧 Environment: Native")

    print("\n" + "=" * 60 + "\n")


# ============================================================================
# Main
# ============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Build Audex DEB package")
    parser.add_argument(
        "version",
        nargs="?",
        help="Version to build (default: read from VERSION file)",
    )
    parser.add_argument(
        "arch",
        nargs="?",
        default="arm64",
        help="Architecture (default: arm64)",
    )
    parser.add_argument(
        "--wsl",
        action="store_true",
        help="WSL mode: build in WSL home directory instead of project dist",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    global WSL_MODE, BUILD_DIR, OUTPUT_DIR

    args = parse_args()
    WSL_MODE = args.wsl

    # Configure paths based on mode
    if not IS_DOCKER:
        SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()  # noqa: N806

        if WSL_MODE:
            # WSL mode: use home directory
            BUILD_DIR = pathlib.Path.home() / "audex-build"
            OUTPUT_DIR = pathlib.Path.home() / "audex-output"
            log_info(f"WSL mode: Output to {OUTPUT_DIR}")
        else:
            # Local mode: use project directory (may fail on Windows mounts)
            BUILD_DIR = SCRIPT_DIR / "build"
            OUTPUT_DIR = SCRIPT_DIR.parent.parent / "dist"

    print(f"{Colors.BLUE}")
    print("╔════════════════════════════════════════════════╗")
    print("║       Audex DEB Package Builder                ║")
    if IS_DOCKER:
        print("║            (Docker Mode)                       ║")
    elif WSL_MODE:
        print("║            (WSL Native Mode)                   ║")
    else:
        print("║            (Local Mode)                        ║")
    print("╚════════════════════════════════════════════════╝")
    print(f"{Colors.NC}\n")

    # Resolve version and architecture
    version = resolve_version(args.version)
    arch = args.arch

    # Build directory
    pkg_dir = BUILD_DIR / f"{PACKAGE_NAME}-{version}"

    try:
        # Build steps
        create_package_structure(pkg_dir)
        copy_template_files(pkg_dir, version, arch)
        copy_icon(pkg_dir)
        deb_file = build_deb_package(pkg_dir, version, arch)

        # Show summary
        show_summary(deb_file, version, arch)

    except Exception as e:
        log_error(f"Build failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
