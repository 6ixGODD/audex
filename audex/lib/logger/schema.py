from __future__ import annotations

import typing as t


class LogRecord(t.TypedDict):
    """Base log record structure that all log entries must include.

    This ensures consistent fields across native and loguru backends.
    """

    timestamp: str
    """ISO 8601 formatted timestamp (YYYY-MM-DD HH:MM:SS)"""

    level: str
    """Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""

    message: str
    """The actual log message."""

    logger: str
    """Logger name/identifier."""


class CodeLocationInfo(t.TypedDict, total=False):
    """Code location information."""

    module: str
    """Module name where the log was created."""

    function: str
    """Function name where the log was created."""

    line: int
    """Line number where the log was created."""

    process: int
    """Process ID."""

    thread: int | str
    """Thread ID or name."""


class ExceptionInfo(t.TypedDict, total=False):
    """Exception information."""

    exception_type: str
    """Exception class name."""

    exception: str
    """Exception message."""

    traceback: str
    """Full exception traceback."""


class StructuredLogRecord(LogRecord):
    """Structured log record with separated location, exception, and
    context fields."""

    location: t.NotRequired[CodeLocationInfo]
    """Code location information."""

    exception: t.NotRequired[ExceptionInfo]
    """Exception information if present."""

    context: t.NotRequired[dict[str, t.Any]]
    """Additional custom context fields."""


def format_log_record(
    timestamp: str,
    level: str,
    message: str,
    logger: str,
    *,
    location: CodeLocationInfo | None = None,
    exception: ExceptionInfo | None = None,
    context: dict[str, t.Any] | None = None,
) -> StructuredLogRecord:
    """Format a log record with standard structure.

    Args:
        timestamp: ISO 8601 formatted timestamp
        level: Log level string
        message: Log message
        logger: Logger name
        location: Optional code location information
        exception: Optional exception information
        context: Additional custom context fields

    Returns:
        StructuredLogRecord with all provided information
    """
    record = StructuredLogRecord(
        timestamp=timestamp,
        level=level,
        message=message,
        logger=logger,
    )

    # Add location info if provided and not empty
    if location:
        filtered_location = {k: v for k, v in location.items() if v is not None}
        if filtered_location:
            record["location"] = CodeLocationInfo(**filtered_location)

    # Add exception info if provided and not empty
    if exception:
        filtered_exception = {k: v for k, v in exception.items() if v is not None}
        if filtered_exception:
            record["exception"] = ExceptionInfo(**filtered_exception)

    # Add context if provided and not empty
    if context:
        record["context"] = context

    return record
