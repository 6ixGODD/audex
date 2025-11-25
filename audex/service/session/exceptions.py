from __future__ import annotations

import typing as t

from audex.exceptions import AudexError
from audex.exceptions import InternalError


class SessionServiceError(AudexError):
    """Base exception for session service errors."""

    default_message = "Session service error"
    code: t.ClassVar[int] = 0x40


class InternalSessionServiceError(InternalError):
    """Internal error in session service."""

    default_message = "Internal session service error"
    code: t.ClassVar[int] = 0x41


class SessionNotFoundError(SessionServiceError):
    """Raised when session is not found."""

    __slots__ = ("message", "session_id")

    default_message = "Session not found"
    code: t.ClassVar[int] = 0x42

    def __init__(self, message: str | None = None, *, session_id: str) -> None:
        """Initialize the exception.

        Args:
            message: Error message. If None, uses default_message with session_id.
            session_id: The ID of the session that was not found.
        """
        self.session_id = session_id
        full_message = message or f"{self.default_message}: {session_id}"
        super().__init__(full_message)


class SegmentNotFoundError(SessionServiceError):
    """Raised when segment is not found."""

    __slots__ = ("message", "segment_id")

    default_message = "Segment not found"
    code: t.ClassVar[int] = 0x43

    def __init__(self, message: str | None = None, *, segment_id: str) -> None:
        """Initialize the exception.

        Args:
            message: Error message. If None, uses default_message with segment_id.
            segment_id: The ID of the segment that was not found.
        """
        self.segment_id = segment_id
        full_message = message or f"{self.default_message}: {segment_id}"
        super().__init__(full_message)


class RecordingError(SessionServiceError):
    """Raised for recording-related errors."""

    default_message = "Recording operation failed"
    code: t.ClassVar[int] = 0x44
