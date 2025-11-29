from __future__ import annotations

import argparse
import pathlib
import sys

import dotenv

from audex.cli.apis import register_apis
from audex.cli.args import parser_with_version
from audex.cli.exceptions import CLIError
from audex.cli.helper import display
from audex.config import Config
from audex.config import build_config
from audex.config import setconfig
from audex.exceptions import AudexError
from audex.utils import flatten_dict


def main() -> int:
    """Main entry point for the Audex CLI.

    This function parses command-line arguments, executes the appropriate
    command, and handles errors gracefully.

    Returns:
        Exit code indicating success or type of failure.
    """

    # Load environment variables from .env file if it exists
    if dotenv.find_dotenv():
        dotenv.load_dotenv()

    try:
        args = parse_args()
        args.func(args)
        return 0
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print()
        display.warning("Cancelled by user")
        return 130
    except CLIError as e:
        # Handle known CLI errors
        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        display.show_error(e, verbose=verbose)
        return e.exit_code
    except AudexError as e:
        # Handle known Audex errors
        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        display.show_error(e, verbose=verbose)
        return e.code
    except Exception as e:
        # Handle unexpected errors
        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        display.show_error(e, verbose=verbose)
        return 1


def parse_args() -> argparse.Namespace:
    parser = parser_with_version()

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    # Add config argument at top level
    parser.add_argument(
        "--config",
        "-c",
        type=pathlib.Path,
        default=None,
        help="Path to the configuration file",
    )

    # Create subparsers for other commands (serve, init, etc.)
    subparsers = parser.add_subparsers(
        title="Available Commands",
        dest="command",
        help="Command to execute (optional, default is to run the application)",
        metavar="<command>",
        required=False,
    )

    # Register other commands (not run, since it's default)
    register_apis(subparsers)

    # Set default function to run the application
    parser.set_defaults(func=run_application)

    return parser.parse_args()


def run_application(args: argparse.Namespace) -> None:
    """Run the main Audex application (default behavior)."""
    from nicegui import core

    core.app.native.start_args.update({"gui": "qt"})

    display.banner("Audex", subtitle="Smart Medical Recording & Transcription System")

    # Bootstrap
    display.step("Bootstrapping application", step=0)
    print()

    # Load configuration
    with display.section("Loading Configuration"):
        if args.config:
            display.info(f"Loading config from: {args.config}")
            display.path(args.config, exists=args.config.exists())

            if args.config.suffix in {".yaml", ".yml"}:
                setconfig(Config.from_yaml(args.config))
                display.success("YAML configuration loaded")
            else:
                from audex.cli.exceptions import InvalidArgumentError

                raise InvalidArgumentError(
                    arg="config",
                    value=args.config,
                    reason=f"Unsupported config file format: {args.config.suffix}."
                    "Supported formats are .yaml, .yml, .json, .jsonc, .json5",
                )
        else:
            display.info("Using default configuration")

    # Show configuration summary
    cfg = build_config()
    with display.section("Application Configuration"):
        display.table_dict(flatten_dict(cfg.model_dump()))

    # Initialize container
    display.step("Initializing application", step=1)
    with display.loading("Wiring dependencies..."):
        from audex.container import Container
        import audex.view.pages

        container = Container()
        container.wire(packages=[audex.view.pages])

    display.success("Application initialized")

    # Launch info
    display.step("Launching application", step=2)
    print()

    import platform

    if cfg.core.app.native:
        display.info("Launching in native window mode")
        display.info(f"GUI Backend: PyQt6 ({platform.system()})")
    else:
        display.info("Application will open in your default browser")

    display.info("Press Ctrl+C to stop")

    # Separator before app logs
    print()
    display.separator()
    print()

    # Start application
    view = container.views().view()
    view.run()


def cli() -> None:
    """Entry point for installed command-line script.

    This function is called when running `audex` as an installed command.
    It's registered in pyproject.toml as a console script entry point.

    Example:
        After installing with pip:

        ```bash
        audex --help
        audex -c .config.yml
        audex serve --port 8080
        ```
    """
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
