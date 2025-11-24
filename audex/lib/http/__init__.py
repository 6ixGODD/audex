from __future__ import annotations

from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin


class HTTPServer(AsyncContextMixin, LoggingMixin):
    __logtag__ = "audex.lib.http"

    def __init__(self):
        super().__init__()
