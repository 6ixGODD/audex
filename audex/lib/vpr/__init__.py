from __future__ import annotations

import abc
import typing as t

from audex.exceptions import AudexError
from audex.helper.mixin import LoggingMixin


class VPR(LoggingMixin, abc.ABC):
    @abc.abstractmethod
    async def create_group(self, name: str, gid: str | None = None) -> str: ...

    @abc.abstractmethod
    async def enroll(
        self,
        data: bytes,
        sr: t.Literal[8000, 16000],
        uid: str | None = None,
    ) -> str: ...

    @abc.abstractmethod
    async def update(self, uid: str, data: bytes, sr: t.Literal[8000, 16000]) -> None: ...

    @abc.abstractmethod
    async def verify(self, uid: str, data: bytes, sr: t.Literal[8000, 16000]) -> float: ...


class VPRError(AudexError):
    default_message = "VPR error occurred"
