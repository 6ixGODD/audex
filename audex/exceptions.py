from __future__ import annotations

import typing as t

import pydantic as pyd


class AudexError(Exception):
    """Base exception for all Audex-related errors.

    Attributes:
        default_message: Default error message for this exception type.
        code: Unique error code identifying this exception type.
        message: The actual error message for this instance.
    """

    __slots__ = ("message",)

    default_message: t.ClassVar[str] = "An error occurred in Audex."
    code: t.ClassVar[int] = 0x01

    def __init__(self, message: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Custom error message. If None, uses default_message.
        """
        self.message = message or self.default_message
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return formatted error string with code."""
        return f"[Error {self.code}] {self.message}"

    def __repr__(self) -> str:
        """Return detailed representation of the exception."""
        return f"{self.__class__.__name__}(code={self.code}, message={self.message!r})"

    def as_dict(self) -> dict[str, t.Any]:
        """Convert exception to dictionary with all slots."""
        data: dict[str, t.Any] = {}
        for slot in getattr(self, "__slots__", []):
            data[slot] = getattr(self, slot, None)
        return data


class InternalError(AudexError):
    """Base exception for internal system errors.

    These errors should NOT expose technical details to users. Frontend
    should display a generic error message and ask users to contact
    support with the error code.
    """

    __slots__ = ("details", "message")

    default_message = "Internal system error occurred"
    code: t.ClassVar[int] = 0x10

    def __init__(self, message: str | None = None, **details: t.Any) -> None:
        """Initialize the exception.

        Args:
            message: Custom error message. If None, uses default_message.
            **details: Additional technical details for logging/debugging.
        """
        self.details = details
        full_message = message or self.default_message
        super().__init__(full_message)


class RequiredModuleNotFoundError(InternalError):
    """Exception raised when a required module is not found."""

    __slots__ = ("details", "message", "module_name")

    default_message = "Required module not found"
    code: t.ClassVar[int] = 0x11

    def __init__(self, *module_name: str, message: str | None = None, **details: t.Any) -> None:
        """Initialize the exception.

        Args:
            *module_name: One or more names of missing modules.
            message: Custom error message. If None, uses formatted
                default_message.
            **details: Additional technical details for logging/debugging.
        """
        self.module_name = module_name
        full_message = message or f"{self.default_message}: {', '.join(module_name)}"
        super().__init__(full_message, **details)


class ConfigurationError(InternalError):
    """Exception raised for configuration errors."""

    __slots__ = ("config_key", "details", "message")

    default_message = "Configuration error occurred"
    code: t.ClassVar[int] = 0x13

    def __init__(
        self, message: str | None = None, *, config_key: str, reason: str, **details: t.Any
    ) -> None:
        """Initialize the exception.

        Args:
            message: Custom error message. If None, uses formatted
                default_message.
            config_key: The configuration key that caused the error.
            reason: Description of the configuration error.
            **details: Additional technical details for logging/debugging.
        """
        self.config_key = config_key
        self.reason = reason
        full_message = message or f"{self.default_message}: [{config_key}] {reason}"
        super().__init__(full_message, **details)


class ValidationError(AudexError):
    """Exception raised for validation errors."""

    __slots__ = ("message", "reason")

    default_message = "Validation failed"
    code: t.ClassVar[int] = 0x12

    def __init__(self, message: str | None = None, *, reason: str) -> None:
        """Initialize the exception.

        Args:
            reason: Description of what failed validation.
            message: Custom error message. If None, uses formatted default_message.
        """
        self.reason = reason
        full_message = message or f"{self.default_message}: {reason}"
        super().__init__(full_message)

    @classmethod
    def from_pydantic_validation_err(cls, err: pyd.ValidationError) -> t.Self:
        """Create ValidationError from a Pydantic ValidationError."""
        reason = "; ".join(f"{e['loc']}: {e['msg']}" for e in err.errors())
        return cls(reason=reason)


class NoActiveSessionError(AudexError):
    """Exception raised when there is no active session."""

    default_message = "No active session found. Please re-login to continue."
    code: t.ClassVar[int] = 0x20


class PermissionDeniedError(AudexError):
    """Exception raised for permission denied errors."""

    default_message = "Permission denied. You do not have access to this resource."
    code: t.ClassVar[int] = 0x21
