from __future__ import annotations

import typing as t

from audex.helper.mixin import LoggingMixin
from audex.lib.session import SessionManager


class BaseService(LoggingMixin):
    __logtag__ = "audex.service"

    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        cls.__logtag__ = f"audex.service:{cls.__name__}"
        super().__init_subclass__(**kwargs)

    def __init__(self, sm: SessionManager):
        super().__init__()
        self.sm = sm
