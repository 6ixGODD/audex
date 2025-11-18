from __future__ import annotations

import enum
import os
import typing as t


class Loglevel(str, enum.Enum):
    """Logging level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def parse(cls, level: str | int) -> Loglevel:
        """Parse a log level from string or integer.

        Args:
            level: The log level as a string or integer.

        Returns:
            The corresponding Loglevel enum member.
        """
        if isinstance(level, int):
            level_map = {
                10: cls.DEBUG,
                20: cls.INFO,
                30: cls.WARNING,
                40: cls.ERROR,
                50: cls.CRITICAL,
            }
            if level in level_map:
                return level_map[level]
            raise ValueError(f"Invalid log level integer: {level}")
        try:
            return cls(level.upper())
        except ValueError:
            raise ValueError(f"Invalid log level string: {level}") from None


class SizeBasedRotation(t.NamedTuple):
    max_size: int
    """Maximum log file size in bytes before rotation occurs."""

    backup_count: int
    """Number of backup log files to keep."""


class TimeBasedRotation(t.NamedTuple):
    interval: int
    """Time interval in seconds for log rotation."""

    backup_count: int
    """Number of backup log files to keep."""


class Rotation(t.NamedTuple):
    size_based: SizeBasedRotation | None = None
    """Size-based rotation configuration."""

    time_based: TimeBasedRotation | None = None
    """Time-based rotation configuration."""


class LoggingTarget(t.NamedTuple):
    logname: t.Literal["stdout", "stderr"] | os.PathLike[str] = "stdout"
    """Name of the logging target, either standard streams or a file
    path."""

    loglevel: Loglevel = Loglevel.INFO
    """Logging level for this target."""

    rotation: Rotation | None = None
    """Log rotation configuration, if applicable."""
