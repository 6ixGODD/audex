from __future__ import annotations

import contextlib
import os
import pathlib
import sys
import traceback
import typing as t

import halo

from audex.cli.helper.ansi import ANSI

# Initialize spinner
spinner = halo.Halo(spinner="dots")


def success(message: str, /, prefix: str = "✓") -> None:
    """Print a success message."""
    print(f"{ANSI.success(prefix)} {message}")


def error(message: str, /, prefix: str = "✗") -> None:
    """Print an error message."""
    print(f"{ANSI.error(prefix)} {message}", file=sys.stderr)


def warning(message: str, /, prefix: str = "⚠") -> None:
    """Print a warning message."""
    print(f"{ANSI.warning(prefix)} {message}")


def info(message: str, /, prefix: str = "•") -> None:
    """Print an info message."""
    print(f"{ANSI.info(prefix)} {message}")


def debug(message: str, /, prefix: str = "→") -> None:
    """Print a debug message (dimmed)."""
    print(ANSI.format(f"{prefix} {message}", ANSI.STYLE.DIM))


def step(message: str, /, step: int | None = None) -> None:
    """Print a step message in a process."""
    if step is not None:
        prefix = ANSI.format(f"[{step}]", ANSI.FG.CYAN, ANSI.STYLE.BOLD)
        print(f"{prefix} {message}")
    else:
        print(f"► {message}")


def path(
    path: str | pathlib.Path | os.PathLike[str],
    /,
    label: str | None = None,
    exists: bool | None = None,
) -> None:
    """Print a formatted file path.

    Args:
        path: The path to display
        label: Optional label to show before the path
        exists: If provided, shows existence indicator (✓ or ✗)
    """
    path = pathlib.Path(path)

    parts = []
    if label:
        parts.append(f"{label}:")

    if exists is not None:
        indicator = "✓" if exists else "✗"
        parts.append(indicator)

    parts.append(str(path))
    print(" ".join(parts))


def command(cmd: str, /) -> None:
    """Print a command being executed."""
    print(ANSI.format(f"$ {cmd}", ANSI.FG.GRAY))


def header(text: str, /, width: int = 60) -> None:
    """Print a section header.

    Args:
        text: Header text
        width: Width of header
    """
    print()
    print(text)
    print("-" * min(len(text), width))


def separator(width: int = 60) -> None:
    """Print a separator line."""
    print("-" * width)


def table(headers: list[str], rows: list[list[str]], /) -> None:
    """Print a simple table.

    Args:
        headers: Column headers
        rows: Table rows
    """
    if not headers or not rows:
        return

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_row = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_row)
    print("-" * len(header_row))

    # Print rows
    for row in rows:
        print(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))


def table_dict(data: dict[str, t.Any], /, headers: tuple[str, str] = ("Key", "Value")) -> None:
    """Print a table from a dictionary.

    Args:
        data: Dictionary to display
        headers: Column headers
    """
    rows = [[str(k), str(v)] for k, v in data.items()]
    table(list(headers), rows)


def list_items(
    items: list[str],
    /,
    bullet: str = "•",
    indent: int = 0,
) -> None:
    """Print a bulleted list of items.

    Args:
        items: List items to display
        bullet: Bullet character
        indent: Indentation level
    """
    indent_str = "  " * indent
    for item in items:
        print(f"{indent_str}{bullet} {item}")


def key_value(
    data: dict[str, t.Any],
    /,
    indent: int = 0,
) -> None:
    """Print key-value pairs in a formatted style.

    Args:
        data: Dictionary of key-value pairs
        indent: Indentation level
    """
    if not data:
        return

    max_key_len = max(len(str(k)) for k in data)
    indent_str = "  " * indent

    for key, value in data.items():
        print(f"{indent_str}{str(key).ljust(max_key_len)} : {value}")


def progress_bar(
    current: int,
    total: int,
    /,
    width: int = 40,
    label: str = "",
) -> None:
    """Print a progress bar.

    Args:
        current: Current progress value
        total: Total/max value
        width: Width of the progress bar
        label: Optional label
    """
    percent = current / total if total > 0 else 0
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)

    parts = []
    if label:
        parts.append(label)
    parts.append(f"[{bar}]")
    parts.append(f"{percent * 100:5.1f}%")
    parts.append(f"({current}/{total})")

    print("\r" + " ".join(parts), end="", flush=True)

    if current >= total:
        print()


@contextlib.contextmanager
def loading(
    text: str = "Loading",
    /,
    success_text: str | None = None,
    error_text: str | None = None,
) -> t.Generator[halo.Halo, None, None]:
    """Context manager for showing a loading spinner.

    Args:
        text: Loading message
        success_text: Message to show on success
        error_text: Message to show on error
    """
    spinner.text = text
    spinner.start()

    try:
        yield spinner
        if success_text:
            spinner.succeed(success_text)
        else:
            spinner.succeed()
    except Exception as e:
        if error_text:
            spinner.fail(error_text)
        else:
            spinner.fail(f"{text} failed: {e}")
        raise
    finally:
        spinner.stop()


@contextlib.contextmanager
def section(title: str, /) -> t.Generator[None, None, None]:
    """Context manager for a named section.

    Args:
        title: Section title
    """
    print()
    print(title)
    print("-" * len(title))

    try:
        yield
    finally:
        print()


def banner(text: str, /, subtitle: str | None = None, version: str | None = None) -> None:
    """Print an application banner.

    Args:
        text: Main banner text
        subtitle: Optional subtitle
        version: Optional version string
    """
    print()
    print(f"=== {text} ===")
    if subtitle:
        print(f"    {subtitle}")
    if version:
        print(f"    v{version}")
    print()


def tree(data: dict[str, t.Any], /, prefix: str = "") -> None:
    """Print a tree structure.

    Args:
        data: Nested dictionary to display as tree
        prefix: Internal use for recursion
    """
    items = list(data.items())

    for i, (key, value) in enumerate(items):
        is_last_item = i == len(items) - 1

        if is_last_item:
            connector = "└── "
            extension = "    "
        else:
            connector = "├── "
            extension = "│   "

        if isinstance(value, dict):
            print(f"{prefix}{connector}{key}")
            tree(value, prefix + extension)
        elif isinstance(value, list):
            print(f"{prefix}{connector}{key}")
            for item in value:
                print(f"{prefix}{extension}• {item}")
        else:
            print(f"{prefix}{connector}{key}: {value}")


def confirm(prompt: str, /, default: bool = False) -> bool:
    """Ask for user confirmation with a yes/no prompt.

    Args:
        prompt: Question to ask
        default: Default answer if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    suffix = "[Y/n]" if default else "[y/N]"
    response = input(f"{prompt} {suffix} ").strip().lower()

    if not response:
        return default

    if response in ("y", "yes"):
        return True
    if response in ("n", "no"):
        return False

    error("Please answer 'y' or 'n'")
    return confirm(prompt, default)


def exception_detail(exc: Exception, /, show_traceback: bool = False) -> None:
    """Display detailed exception information.

    Args:
        exc: Exception to display
        show_traceback: Whether to show full traceback
    """
    from audex.exceptions import AudexError

    print()
    print("=" * 70)
    print(f"ERROR: {type(exc).__name__}")

    if isinstance(exc, AudexError):
        print(f"Code: {exc.code}")

    print("-" * 70)
    print(f"Message: {exc}")
    print("=" * 70)

    if show_traceback:
        print()
        print("Traceback:")
        print("-" * 70)
        traceback.print_exception(type(exc), exc, exc.__traceback__)


def error_summary(
    title: str,
    /,
    details: dict[str, str] | None = None,
    suggestions: list[str] | None = None,
) -> None:
    """Display an error summary with optional details and suggestions.

    Args:
        title: Error title/summary
        details: Optional dictionary of error details
        suggestions: Optional list of suggestions to fix the error
    """
    print()
    print(f"✗ {title}")
    print()

    if details:
        print("Details:")
        key_value(details, indent=1)
        print()

    if suggestions:
        print("Suggestions:")
        list_items(suggestions, bullet="→", indent=1)
        print()


def fatal_error(message: str, /, exit_code: int = 1) -> t.NoReturn:
    """Display a fatal error and exit.

    Args:
        message: Error message
        exit_code: Exit code
    """
    print()
    print("=" * 70)
    print("FATAL ERROR")
    print("=" * 70)
    print(f"  {message}")
    print("=" * 70)
    print()
    sys.exit(exit_code)


def show_error(exc: Exception, verbose: bool = False) -> None:
    """Display error information.

    Args:
        exc: Exception to display
        verbose: Show full traceback
    """
    from audex.exceptions import AudexError

    error(f"{type(exc).__name__}: {exc}")

    if isinstance(exc, AudexError):
        info(f"Error code: {exc.code}")

    if verbose:
        print("\nTraceback:")
        traceback.print_exception(type(exc), exc, exc.__traceback__)
