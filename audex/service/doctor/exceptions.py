from __future__ import annotations

import typing as t

from audex.exceptions import AudexError
from audex.exceptions import InternalError


class DoctorServiceError(AudexError):
    """Base exception for doctor service errors."""

    default_message = "Doctor service error"
    code: t.ClassVar[int] = 0x30


class InternalDoctorServiceError(InternalError):
    """Internal error in doctor service."""

    default_message = "Internal doctor service error"
    code: t.ClassVar[int] = 0x31


class DoctorNotFoundError(DoctorServiceError):
    """Raised when doctor is not found."""

    __slots__ = ("doctor_id", "message")

    default_message = "Doctor not found"
    code: t.ClassVar[int] = 0x32

    def __init__(self, message: str, *, doctor_id: str) -> None:
        """Initialize the exception.

        Args:
            message: Error message (typically in Chinese for users).
            doctor_id: The ID of the doctor that was not found.
        """
        self.doctor_id = doctor_id
        super().__init__(message)


class InvalidCredentialsError(DoctorServiceError):
    """Raised for invalid login credentials."""

    __slots__ = ("message", "reason")

    default_message = "Invalid credentials"
    code: t.ClassVar[int] = 0x33

    def __init__(self, message: str, *, reason: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message (typically in Chinese for users).
            reason: Machine-readable reason code (from InvalidCredentialReasons).
        """
        self.reason = reason
        super().__init__(message)


class VoiceprintNotFoundError(DoctorServiceError):
    """Raised when voiceprint is not found."""

    __slots__ = ("doctor_id", "message")

    default_message = "Voiceprint not found"
    code: t.ClassVar[int] = 0x34

    def __init__(self, message: str, *, doctor_id: str) -> None:
        """Initialize the exception.

        Args:
            message: Error message (typically in Chinese for users).
            doctor_id: The ID of the doctor whose voiceprint was not found.
        """
        self.doctor_id = doctor_id
        super().__init__(message)


class DuplicateEIDError(DoctorServiceError):
    """Raised when trying to register with an existing EID."""

    __slots__ = ("eid", "message")

    default_message = "Duplicate EID"
    code: t.ClassVar[int] = 0x35

    def __init__(self, message: str, *, eid: str) -> None:
        """Initialize the exception.

        Args:
            message: Error message (typically in Chinese for users).
            eid: The duplicate employee ID.
        """
        self.eid = eid
        super().__init__(message)
