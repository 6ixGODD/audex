from __future__ import annotations

from audex.exceptions import AudexError


class WebsocketError(AudexError, RuntimeError):
    __slots__ = ()
    code = 1000
    default_message = "A WebSocket error occurred"
