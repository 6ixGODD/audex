from __future__ import annotations

import asyncio
import types
import typing as t

from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import AsyncLifecycleMixin
from audex.helper.mixin import ContextMixin
from audex.helper.mixin import LifecycleMixin
from audex.helper.mixin import LoggingMixin


class LifeSpan(LoggingMixin):
    __logtag__ = "audex.lifespan"

    def __init__(self, *contexts: object) -> None:
        super().__init__()
        self.contexts = contexts

    def append(self, context: object) -> None:
        self.contexts += (context,)

    async def startup(self) -> t.Self:
        atasks: list[t.Coroutine[None, None, None]] = []
        for ctx in self.contexts:
            if isinstance(ctx, ContextMixin):
                self.logger.info(f"Initializing context: {ctx!r}")
                ctx.init()
            elif isinstance(ctx, AsyncContextMixin):
                self.logger.info(f"Async initializing context: {ctx!r}")
                atasks.append(ctx.init())

            if isinstance(ctx, LifecycleMixin):
                self.logger.info(f"Starting lifecycle: {ctx!r}")
                ctx.start()
            elif isinstance(ctx, AsyncLifecycleMixin):
                self.logger.info(f"Async starting lifecycle: {ctx!r}")
                atasks.append(ctx.start())

        if atasks:
            await asyncio.gather(*atasks)

        return self

    async def __aenter__(self) -> t.Self:
        return await self.startup()

    async def shutdown(self) -> None:
        atasks: list[t.Coroutine[None, None, None]] = []
        for ctx in self.contexts:
            if isinstance(ctx, ContextMixin):
                self.logger.info(f"Closing context: {ctx!r}")
                ctx.close()
            elif isinstance(ctx, AsyncContextMixin):
                self.logger.info(f"Async closing context: {ctx!r}")
                atasks.append(ctx.close())

            if isinstance(ctx, LifecycleMixin):
                self.logger.info(f"Stopping lifecycle: {ctx!r}")
                ctx.stop()
            elif isinstance(ctx, AsyncLifecycleMixin):
                self.logger.info(f"Async stopping lifecycle: {ctx!r}")
                atasks.append(ctx.stop())

        if atasks:
            await asyncio.gather(*atasks)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        await self.shutdown()
