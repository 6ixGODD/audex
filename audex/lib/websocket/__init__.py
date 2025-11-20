from __future__ import annotations

from audex.exceptions import AudexError


class WebsocketError(AudexError, RuntimeError):
    __slots__ = ()
    code = 0x9001
    default_message = "A WebSocket error occurred"
