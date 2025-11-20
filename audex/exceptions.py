from __future__ import annotations

import typing as t

import pydantic as pyd


class AudexError(Exception):
    """Base exception for all Audex-related errors.

    This is the root exception class for the Audex library. All custom exceptions
    in Audex inherit from this class, making it easy to catch any Audex-specific
    error.

    Each exception has an associated error code for programmatic error handling
    and a default message that can be overridden.

    Attributes:
        default_message: Default error message for this exception type.
        code: Unique error code identifying this exception type.
        message: The actual error message for this instance.

    Example:
        ```python
        from audex.exceptions import AudexError

        try:
            # Some Audex operation
            pass
        except AudexError as e:
            print(f"Audex error occurred: {e}")
            print(f"Error code: {e.code}")
        ```

    Example:
        ```python
        # Create custom exception
        class CustomError(AudexError):
            default_message = "Custom error occurred"
            code = 999


        raise CustomError("Something went wrong")
        ```
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
        super().__init__(message)

    def __str__(self) -> str:
        """Return formatted error string with code.

        Returns:
            Formatted string in the form "[Error {code}] {message}".
        """
        return f"[Error {self.code}] {self.message}"

    def __repr__(self) -> str:
        """Return detailed representation of the exception.

        Returns:
            String showing class name, code, and message.
        """
        return f"{self.__class__.__name__}(code={self.code}, message={self.message!r})"


class RequiredModuleNotFoundError(AudexError):
    """Exception raised when a required module is not found.

    This exception is raised when attempting to use functionality that requires
    optional dependencies (e.g., torch, torchvision, PIL) that are not installed.

    Attributes:
        default_message: Template for the default error message.
        code: Error code 2.
        module_name: Tuple of missing module names.
    """

    default_message = "Required module {module_name} not found. Please install it to proceed."
    code: t.ClassVar[int] = 0x02

    def __init__(self, *module_name: str, message: str | None = None) -> None:
        """Initialize the exception.

        Args:
            *module_name: One or more names of missing modules.
            message: Custom error message. If None, uses formatted default_message.
        """
        self.module_name = module_name
        full_message = message or self.default_message.format(module_name=module_name)
        super().__init__(full_message)

    def __repr__(self) -> str:
        """Return detailed representation of the exception.

        Returns:
            String showing class name, module names, and message.
        """
        return (
            f"{self.__class__.__name__}(module_name={self.module_name!r}, message={self.message!r})"
        )


class ValidationError(AudexError):
    """Exception raised for validation errors.

    Raised when data fails validation checks, such as invalid split ratios,
    malformed bounding boxes, or constraint violations.

    Attributes:
        default_message: Template for the default error message.
        code: Error code 20.
        reason: Description of what failed validation.

    Example:
        ```python
        from audex.exceptions import ValidationError
        from audex.dataset.types import SplitRatio

        try:
            split = SplitRatio(0.5, 0.3, 0.1)
            split.validate()
        except ValidationError as e:
            print(f"Validation failed: {e.reason}")
        ```

    Example:
        ```python
        # Raise for invalid bbox
        raise ValidationError(
            reason="x_max must be greater than x_min",
            message="Invalid bounding box coordinates",
        )
        ```
    """

    default_message = "Validation failed: {reason}"
    code: t.ClassVar[int] = 0x14

    def __init__(self, reason: str, message: str | None = None) -> None:
        """Initialize the exception.

        Args:
            reason: Description of what failed validation.
            message: Custom error message. If None, uses formatted default_message.
        """
        self.reason = reason
        full_message = message or self.default_message.format(reason=reason)
        super().__init__(full_message)

    @classmethod
    def from_pydantic_validation_err(cls, err: pyd.ValidationError) -> t.Self:
        """Create ValidationError from a Pydantic ValidationError.

        Args:
            err: The Pydantic ValidationError instance.

        Returns:
            An instance of ValidationError with details from the Pydantic error.
        """
        reason = "; ".join(f"{e['loc']}: {e['msg']}" for e in err.errors())
        return cls(reason=reason)
