from __future__ import annotations

import abc

from audex.exceptions import AudexError
from audex.helper.mixin import LoggingMixin


class VPR(LoggingMixin, abc.ABC):
    group_id: str | None

    def __init__(self, group_id: str | None = None) -> None:
        super().__init__()
        self.group_id = group_id

    @abc.abstractmethod
    async def create_group(self, name: str, gid: str | None = None) -> str: ...

    @abc.abstractmethod
    async def enroll(self, data: bytes, sr: int, uid: str | None = None) -> str: ...

    @abc.abstractmethod
    async def update(self, uid: str, data: bytes, sr: int) -> None: ...

    @abc.abstractmethod
    async def verify(self, uid: str, data: bytes, sr: int) -> float: ...


class VPRError(AudexError):
    default_message = "VPR error occurred"


class GroupAlreadyExistsError(VPRError):
    default_message = "VPR group already exists"


class GroupNotFoundError(VPRError):
    default_message = "VPR group not found"
