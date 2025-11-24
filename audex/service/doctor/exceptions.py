from __future__ import annotations

from audex.exceptions import AudexError
from audex.service.doctor.const import InvalidCredentialReasons


class DoctorServiceError(AudexError):
    default_message = "An error occurred in the doctor service."


class DoctorNotFoundError(DoctorServiceError):
    __slots__ = ("doctor_id", "message")
    default_message = "Doctor {doctor_id} not found."

    def __init__(self, message: str | None = None, *, doctor_id: str) -> None:
        if message is None:
            message = self.default_message.format(doctor_id=doctor_id)
        super().__init__(message)
        self.doctor_id = doctor_id


class InvalidCredentialsError(DoctorServiceError):
    __slots__ = ("message", "reason")
    default_message = "Invalid credentials provided for doctor service: {reason}."

    def __init__(
        self,
        message: str | None = None,
        *,
        reason: str = InvalidCredentialReasons.DEFAULT,
    ) -> None:
        if message is None:
            message = self.default_message.format(reason=reason)
        super().__init__(message)
