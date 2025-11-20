from __future__ import annotations

import datetime
import enum
import os
import sys
import typing as t
import uuid

from pydantic import BaseModel
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema
from pydantic_core.core_schema import no_info_plain_validator_function
from pydantic_core.core_schema import plain_serializer_function_ser_schema


def gen_id(prefix: str = "", suffix: str = "", without_hyphen: bool = True, digis: int = 32) -> str:
    """Generate a unique identifier (UUID) with optional prefix and
    suffix.

    Args:
        prefix: A string to prepend to the generated UUID (default: "").
        suffix: A string to append to the generated UUID (default: "").
        without_hyphen: Whether to remove hyphens from the UUID
            (default: True).
        digis: Number of digits to include from the UUID (default: 32).

    Returns:
        A unique identifier string with the specified prefix and suffix.
    """
    uid = uuid.uuid4()
    uid_str = uid.hex if without_hyphen else str(uid)
    uid_str = uid_str[:digis]
    return f"{prefix}{uid_str}{suffix}"


def utcnow() -> datetime.datetime:
    """Get the current UTC datetime with timezone info.

    Returns:
        The current UTC datetime with timezone info.
    """
    return datetime.datetime.now(datetime.UTC)


class ANSI:
    """Enhanced formatter for ANSI color and style formatting in console
    output.

    Provides organized color constants, helper methods, and context
    managers for applying consistent styling to terminal output.
    Automatically detects color support in the terminal environment.
    """

    class FG(enum.StrEnum):
        """Foreground colors."""

        BLACK = "\033[30m"
        RED = "\033[31m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        BLUE = "\033[34m"
        MAGENTA = "\033[35m"
        CYAN = "\033[36m"
        WHITE = "\033[37m"
        GRAY = "\033[90m"
        BRIGHT_RED = "\033[91m"
        BRIGHT_GREEN = "\033[92m"
        BRIGHT_YELLOW = "\033[93m"
        BRIGHT_BLUE = "\033[94m"
        BRIGHT_MAGENTA = "\033[95m"
        BRIGHT_CYAN = "\033[96m"
        BRIGHT_WHITE = "\033[97m"

    class BG(enum.StrEnum):
        """Background colors."""

        BLACK = "\033[40m"
        RED = "\033[41m"
        GREEN = "\033[42m"
        YELLOW = "\033[43m"
        BLUE = "\033[44m"
        MAGENTA = "\033[45m"
        CYAN = "\033[46m"
        WHITE = "\033[47m"
        GRAY = "\033[100m"
        BRIGHT_RED = "\033[101m"
        BRIGHT_GREEN = "\033[102m"
        BRIGHT_YELLOW = "\033[103m"
        BRIGHT_BLUE = "\033[104m"
        BRIGHT_MAGENTA = "\033[105m"
        BRIGHT_CYAN = "\033[106m"
        BRIGHT_WHITE = "\033[107m"

    class STYLE(enum.StrEnum):
        """Text styles."""

        RESET = "\033[0m"
        BOLD = "\033[1m"
        DIM = "\033[2m"
        ITALIC = "\033[3m"
        UNDERLINE = "\033[4m"
        BLINK = "\033[5m"
        REVERSE = "\033[7m"
        HIDDEN = "\033[8m"
        STRIKETHROUGH = "\033[9m"

    # For backward compatibility
    RESET = STYLE.RESET
    BOLD = STYLE.BOLD
    UNDERLINE = STYLE.UNDERLINE
    REVERSED = STYLE.REVERSE
    RED = FG.BRIGHT_RED
    GREEN = FG.BRIGHT_GREEN
    YELLOW = FG.BRIGHT_YELLOW
    BLUE = FG.BRIGHT_BLUE
    MAGENTA = FG.BRIGHT_MAGENTA
    CYAN = FG.BRIGHT_CYAN
    WHITE = FG.BRIGHT_WHITE

    # Control whether ANSI colors are enabled
    _enabled = True

    @classmethod
    def supports_color(cls) -> bool:
        """Determine if the current terminal supports colors.

        Returns:
            bool: True if the terminal supports colors, False otherwise.
        """
        # Check for NO_COLOR environment variable (https://no-color.org/)
        if os.environ.get("NO_COLOR", ""):
            return False

        # Check for explicit color control
        if os.environ.get("FORCE_COLOR", ""):
            return True

        # Check if stdout is a TTY
        return hasattr(sys.stdout, "isatty") or sys.stdout.isatty()

    @classmethod
    def enable(cls, enabled: bool = True) -> None:
        """Enable or disable ANSI formatting.

        Args:
            enabled: True to enable colors, False to disable.
        """
        cls._enabled = enabled and cls.supports_color()

    @classmethod
    def format(cls, text: str, /, *styles: STYLE | FG | BG | None) -> str:
        """Format text with the specified ANSI styles.

        Intelligently reapplies styles after any reset sequences in the text.
        If colors are disabled, returns the original text without formatting.

        Args:
            text: The text to format.
            *styles: One or more ANSI style codes to apply.

        Returns:
            The formatted text with ANSI styles applied.
        """
        if not cls._enabled or not styles:
            return text
        if any(s is None for s in styles):
            styles = tuple(s for s in styles if s is not None)

        style_str = "".join(styles)

        # Handle text that already contains reset codes
        if cls.STYLE.RESET in text:
            text = text.replace(cls.STYLE.RESET, f"{cls.STYLE.RESET}{style_str}")

        return f"{style_str}{text}{cls.STYLE.RESET}"

    @classmethod
    def success(cls, text: str, /) -> str:
        """Format text as a success message (green, bold)."""
        return cls.format(text, cls.FG.BRIGHT_GREEN, cls.STYLE.BOLD)

    @classmethod
    def error(cls, text: str, /) -> str:
        """Format text as an error message (red, bold)."""
        return cls.format(text, cls.FG.BRIGHT_RED, cls.STYLE.BOLD)

    @classmethod
    def warning(cls, text: str, /) -> str:
        """Format text as a warning message (yellow, bold)."""
        return cls.format(text, cls.FG.BRIGHT_YELLOW, cls.STYLE.BOLD)

    @classmethod
    def info(cls, text: str, /) -> str:
        """Format text as an info message (cyan)."""
        return cls.format(text, cls.FG.BRIGHT_CYAN)

    @classmethod
    def highlight(cls, text: str, /) -> str:
        """Format text as highlighted (magenta, bold)."""
        return cls.format(text, cls.FG.BRIGHT_MAGENTA, cls.STYLE.BOLD)

    @classmethod
    def rgb(cls, text: str, /, r: int, g: int, b: int, background: bool = False) -> str:
        """Format text with a specific RGB color.

        Args:
            text: The text to format
            r: R
            g: G
            b: B
            background: If True, set as background color instead of foreground

        Returns:
            Formatted text with the specified RGB color
        """
        if not cls._enabled:
            return text

        code = 48 if background else 38
        color_seq = f"\033[{code};2;{r};{g};{b}m"
        return f"{color_seq}{text}{cls.STYLE.RESET}"


def flatten_dict(
    m: t.Mapping[str, t.Any],
    /,
    sep: str = ".",
    _parent: str = "",
) -> dict[str, t.Any]:
    """Flatten a nested dictionary into a single-level dictionary with
    dot-separated keys.

    Args:
        m: The nested dictionary to flatten.
        sep: The separator to use between keys (default: '.').
        _parent: The parent key prefix (used for recursion).

    Returns:
        A flattened dictionary with dot-separated keys.
    """
    items = []  # type: list[tuple[str, t.Any]]
    for k, v in m.items():
        key = f"{_parent}{sep}{k}" if _parent else k
        if isinstance(v, t.Mapping):
            items.extend(flatten_dict(v, _parent=key, sep=sep).items())
        else:
            items.append((key, v))
    return dict(items)


class Unset:
    """A singleton class representing an unset value, distinct from
    None.

    This class is used to indicate that a value has not been set or
    provided, allowing differentiation between an explicit None value
    and an unset state.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<UNSET>"

    __str__ = __repr__

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Unset)

    def __hash__(self) -> int:
        return hash("UNSET")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[BaseModel], handler: GetCoreSchemaHandler, /
    ) -> CoreSchema:
        return no_info_plain_validator_function(
            lambda v: v if isinstance(v, Unset) else UNSET,
            serialization=plain_serializer_function_ser_schema(lambda v: str(v)),
        )


UNSET = Unset()
