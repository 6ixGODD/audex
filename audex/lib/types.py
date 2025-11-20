from __future__ import annotations

import abc
import enum
import typing as t


class SessionState(enum.Enum):
    IDLE, ACTIVE, CLOSED = "IDLE", "ACTIVE", "CLOSED"


class Session(abc.ABC):
    @abc.abstractmethod
    async def start(self) -> None: ...

    @abc.abstractmethod
    async def close(self) -> None: ...

    async def __aenter__(self) -> Session:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: t.Any | None,
    ) -> None:
        await self.close()


S = t.TypeVar("S")
R = t.TypeVar("R")


class DuplexSession(Session, t.Generic[S, R], abc.ABC):
    @abc.abstractmethod
    async def finish(self) -> None: ...

    @abc.abstractmethod
    async def send(self, message: S) -> None: ...

    @abc.abstractmethod
    def receive(self) -> t.AsyncIterable[R]: ...
