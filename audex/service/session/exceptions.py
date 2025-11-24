from __future__ import annotations

from audex.exceptions import AudexError


class SessionServiceError(AudexError):
    default_message = "An error occurred in the session service."


class SessionNotFoundError(SessionServiceError):
    default_message = "Session {session_id} not found."

    def __init__(self, message: str | None = None, *, session_id: str):
        if message is None:
            message = self.default_message.format(session_id=session_id)
        super().__init__(message)
