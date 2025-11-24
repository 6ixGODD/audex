from __future__ import annotations

from audex.helper.mixin import LoggingMixin
from audex.lib.session import SessionManager


class BaseService(LoggingMixin):
    def __init__(self, session: SessionManager):
        super().__init__()
        self.session = session
