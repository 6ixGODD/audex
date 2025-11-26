from __future__ import annotations

import argparse
import sys

from audex.cli.apis import register_apis
from audex.cli.args import parser_with_version
from audex.cli.exceptions import CLIError
from audex.cli.helper import display
from audex.exceptions import AudexError


def main() -> int:
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

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title="Available Commands",
        dest="command",
        help="Command to execute",
        metavar="<command>",
        required=False,  # Allow running without command to show help
    )

    # Register all commands
    register_apis(subparsers)

    # Set default function to print help
    parser.set_defaults(func=lambda _: parser.print_help())

    return parser.parse_args()
