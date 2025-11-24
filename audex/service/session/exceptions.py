from __future__ import annotations

from audex.exceptions import AudexError


class SessionServiceError(AudexError):
    default_message = "An error occurred in the session service."


class SessionNotFoundError(SessionServiceError):
    default_message = "Session not found."
