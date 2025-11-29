#!/usr/bin/env python3
"""Build DEB package inside Docker container.

This script creates a DEB package structure with:
- DEBIAN control files
- Launcher scripts
- Desktop integration files
- Icons

The version is read from the VERSION file in the project root.
The actual audex package will be installed from PyPI during postinst.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys

# ============================================================================
# Configuration
# ============================================================================

BUILD_DIR = pathlib.Path("/build")
TEMPLATES_DIR = BUILD_DIR / "templates"
OUTPUT_DIR = BUILD_DIR / "output"
VERSION_FILE = BUILD_DIR / "VERSION"  # Mounted from project root

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

    directories = [
        pkg_dir / "DEBIAN",
        pkg_dir / "usr" / "bin",
        pkg_dir / "usr" / "lib" / "audex",  # Empty, venv created in postinst
        pkg_dir / "usr" / "share" / "applications",
        pkg_dir / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps",
        pkg_dir / "usr" / "share" / "doc" / "audex",
        pkg_dir / "usr" / "share" / "systemd" / "user",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    log_success("Package structure created")


def copy_template_files(pkg_dir: pathlib.Path, version: str, arch: str) -> None:
    """Copy and process template files."""
    log_step("Copying template files...")

    # Copy DEBIAN scripts
    for script in ["postinst", "prerm", "postrm"]:
        src = TEMPLATES_DIR / "DEBIAN" / script
        dst = pkg_dir / "DEBIAN" / script
        shutil.copy2(src, dst)
        dst.chmod(0o755)

    # Process control template
    control_template = TEMPLATES_DIR / "DEBIAN" / "control.template"
    control_dst = pkg_dir / "DEBIAN" / "control"

    control_content = control_template.read_text()
    control_content = control_content.replace("{VERSION}", version)
    control_content = control_content.replace("{ARCH}", arch)

    control_dst.write_text(control_content)

    # Copy launcher scripts
    for script in ["audex", "audex-setup"]:
        src = TEMPLATES_DIR / "usr" / "bin" / script
        dst = pkg_dir / "usr" / "bin" / script
        shutil.copy2(src, dst)
        dst.chmod(0o755)

    # Copy desktop file
    shutil.copy2(
        TEMPLATES_DIR / "usr" / "share" / "applications" / "audex.desktop",
        pkg_dir / "usr" / "share" / "applications" / "audex.desktop",
    )

    # Copy systemd service
    shutil.copy2(
        TEMPLATES_DIR / "usr" / "share" / "systemd" / "user" / "audex.service",
        pkg_dir / "usr" / "share" / "systemd" / "user" / "audex.service",
    )

    log_success("Template files copied")


def copy_icon(pkg_dir: pathlib.Path) -> None:
    """Copy application icon if available."""
    log_step("Copying icon...")

    icon_src = BUILD_DIR / "logo.svg"
    icon_dst = pkg_dir / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps" / "audex.svg"

    if icon_src.exists():
        shutil.copy2(icon_src, icon_dst)
        log_success("Icon copied")
    else:
        log_warn("Icon not found, creating placeholder")
        placeholder = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
  <circle cx="24" cy="24" r="20" fill="#1976d2"/>
  <text x="24" y="32" font-size="24" fill="white" text-anchor="middle" font-family="sans-serif" font-weight="bold">A</text>
</svg>"""
        icon_dst.write_text(placeholder)


def build_deb_package(pkg_dir: pathlib.Path, version: str, arch: str) -> pathlib.Path:
    """Build the DEB package."""
    log_step("Building DEB package...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    deb_file = OUTPUT_DIR / f"{PACKAGE_NAME}_{version}_{arch}.deb"

    if deb_file.exists():
        deb_file.unlink()

    run_command(["dpkg-deb", "--build", str(pkg_dir), str(deb_file)])

    log_success(f"DEB package built: {deb_file.name}")
    return deb_file


def show_summary(deb_file: pathlib.Path, version: str, arch: str) -> None:
    """Show build summary."""
    print("\n" + "=" * 60)
    log_success("Build Complete!")
    print("=" * 60)
    print(f"\n📦 Package: {deb_file.name}")
    print(f"📊 Size: {deb_file.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"📁 Location: /build/output/{deb_file.name}")
    print(f"\n🔖 Version: {version}")
    print(f"🏗️  Architecture: {arch}")
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
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    print(f"{Colors.BLUE}")
    print("╔════════════════════════════════════════════════╗")
    print("║       Audex DEB Package Builder               ║")
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
        sys.exit(1)


if __name__ == "__main__":
    main()
