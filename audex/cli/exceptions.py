from __future__ import annotations

import typing as t

from pydantic import ValidationError

from audex.exceptions import AudexError


class CLIError(AudexError):
    exit_code: t.ClassVar[int] = 1
    default_message = "An error occurred in Audex CLI."


class InvalidArgumentError(CLIError):
    default_message = "Invalid argument provided: {arg}={value!r}\nReason: {reason}"

    def __init__(self, message: str | None = None, *, arg: str, value: t.Any, reason: str) -> None:
        if message is None:
            message = self.default_message.format(arg=arg, value=value, reason=reason)
        super().__init__(message)

    @classmethod
    def from_validation_error(cls, error: ValidationError) -> t.Self:
        errors = "; ".join(
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in error.errors()
        )
        return cls(
            arg="; ".join(str(loc) for loc in error.errors()[0]["loc"]),
            value="; ".join(
                str(err["ctx"]["given"]) for err in error.errors() if "given" in err.get("ctx", {})
            ),
            reason=errors,
        )
