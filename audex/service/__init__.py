from __future__ import annotations

import typing as t

from audex.helper.mixin import LoggingMixin
from audex.lib.cache import KVCache
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.session import SessionManager


class BaseService(LoggingMixin):
    __logtag__ = "audex.service"

    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        cls.__logtag__ = f"audex.service:{cls.__name__}"
        super().__init_subclass__(**kwargs)

    def __init__(
        self,
        session_manager: SessionManager,
        cache: KVCache,
        doctor_repo: DoctorRepository,
    ):
        super().__init__()
        self.session_manager = session_manager
        self.cache = cache
        self.doctor_repo = doctor_repo
