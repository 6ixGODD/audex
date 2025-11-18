from __future__ import annotations

import inspect
import types
import typing as t

if t.TYPE_CHECKING:
    from audex.logger import Logger


class AsyncContextMixin:
    async def init(self) -> None: ...
    async def close(self) -> None: ...

    async def __aenter__(self) -> t.Self:
        await self.init()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> t.Literal[False]:
        await self.close()
        return False


class ContextMixin:
    def init(self) -> None: ...
    def close(self) -> None: ...

    def __enter__(self) -> t.Self:
        self.init()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> t.Literal[False]:
        self.close()
        return False


class LoggingMixin:
    __logtag__: t.ClassVar[str]

    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        if not inspect.isabstract(cls) and not getattr(cls, "__logtag__", None):
            raise TypeError(f"{cls.__name__} must define __logtag__ class variable")

    def __init__(self, *args: t.Any, logger: Logger | None = None, **kwargs: t.Any) -> None:
        if logger is not None:
            self.logger = logger.with_tag(self.__logtag__)
        super().__init__(*args, **kwargs)

    def setup_log(self, logger: Logger) -> None:
        self.logger = logger.with_tag(self.__logtag__)
