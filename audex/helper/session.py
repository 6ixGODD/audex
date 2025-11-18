from __future__ import annotations

import abc
import enum
import types
import typing as t


class SessionState(enum.Enum):
    IDLE, ACTIVE, CLOSED = range(3)


class Session(abc.ABC):
    def __init__(self):
        self.state = SessionState.IDLE

    @property
    def alive(self) -> bool:
        return self.state == SessionState.ACTIVE

    async def __aenter__(self) -> t.Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> t.Literal[False]:
        await self.close()
        return False

    @abc.abstractmethod
    async def start(self) -> None: ...

    @abc.abstractmethod
    async def close(self) -> None: ...

    @abc.abstractmethod
    async def cleanup(self) -> None: ...


_S = t.TypeVar("_S")
_R = t.TypeVar("_R", bound=t.AsyncIterable)


class DuplexSession(Session, abc.ABC, t.Generic[_S, _R]):
    async def close(self) -> None:
        try:
            if self.state == SessionState.ACTIVE:
                await self.finish()
        finally:
            await self.cleanup()
            self.state = SessionState.CLOSED

    @abc.abstractmethod
    async def finish(self) -> None: ...

    @abc.abstractmethod
    async def send(self, data: _S) -> None: ...

    @abc.abstractmethod
    def recv(self) -> _R: ...
