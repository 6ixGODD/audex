from __future__ import annotations

import typing as t

_T = t.TypeVar("_T")
_U = t.TypeVar("_U")
_V = t.TypeVar("_V")


class AsyncStream(t.AsyncIterable[_T], t.Generic[_T]):
    def __init__(self, source: t.AsyncIterable[_V], mapper: t.Callable[[_V], _T] | None = None):
        self._source = source
        self._mapper = mapper
        self._is_consumed = False
        self._items = []  # type: t.List[_T]
        self._error = None  # type: t.Optional[Exception]
        self._completed = False
        self._iterator = None  # type: t.Optional[t.AsyncIterator[_T]]

    async def __aiter__(self) -> t.AsyncIterator[_T]:  # pylint: disable=invalid-overridden-method
        if self._is_consumed:
            # If the stream has already been consumed, return the cached items
            for item in self._items:
                yield item
            return

        self._is_consumed = True
        try:
            async for raw_item in self._source:
                item = self._mapper(raw_item) if self._mapper else t.cast(_T, raw_item)

                self._items.append(item)
                yield item

        except Exception as e:
            self._error = e
            raise
        finally:
            self._completed = True

    async def __anext__(self) -> _T:
        if not hasattr(self, "_iterator") or self._iterator is None:
            self._iterator = self.__aiter__()
        return await self._iterator.__anext__()

    def filter(self, predicate: t.Callable[[_T], bool]) -> AsyncStream[_T]:
        async def filtered_source() -> t.AsyncIterator[_T]:
            async for item in self:
                if predicate(item):
                    yield item

        return AsyncStream(filtered_source())

    def tap(self, action: t.Callable[[_T], None]) -> AsyncStream[_T]:
        async def tap_source() -> t.AsyncIterator[_T]:
            async for item in self:
                action(item)
                yield item

        return AsyncStream(tap_source())

    def map(self, mapper: t.Callable[[_T], _U]) -> AsyncStream[_U]:
        async def mapped_source() -> t.AsyncIterator[_U]:
            async for item in self:
                yield mapper(item)

        return AsyncStream(mapped_source())

    def take(self, n: int, /) -> AsyncStream[_T]:
        async def take_source() -> t.AsyncIterator[_T]:
            count = 0
            async for item in self:
                if count >= n:
                    break
                yield item
                count += 1

        return AsyncStream(take_source())

    def skip(self, n: int, /) -> AsyncStream[_T]:
        async def skip_source() -> t.AsyncIterator[_T]:
            count = 0
            async for item in self:
                if count < n:
                    count += 1
                    continue
                yield item

        return AsyncStream(skip_source())

    def chunk(self, size: int) -> AsyncStream[list[_T]]:
        async def chunk_source() -> t.AsyncIterator[list[_T]]:
            batch = []
            async for item in self:
                batch.append(item)
                if len(batch) >= size:
                    yield batch
                    batch = []
            if batch:
                yield batch

        return AsyncStream(chunk_source())

    def take_while(self, predicate: t.Callable[[_T], bool]) -> AsyncStream[_T]:
        async def take_while_source() -> t.AsyncIterator[_T]:
            async for item in self:
                if not predicate(item):
                    break
                yield item

        return AsyncStream(take_while_source())

    def enumerate(self, start: int = 0) -> AsyncStream[tuple[int, _T]]:
        async def enumerate_source() -> t.AsyncIterator[tuple[int, _T]]:
            index = start
            async for item in self:
                yield index, item
                index += 1

        return AsyncStream(enumerate_source())

    async def foreach(self, action: t.Callable[[_T], t.Awaitable[None]], /) -> None:
        async for item in self:
            await action(item)

    async def reduce(self, func: t.Callable[[_U, _T], _U], initial: _U) -> _U:
        result = initial
        async for item in self:
            result = func(result, item)
        return result

    async def all(self, predicate: t.Callable[[_T], bool] | None = None, /) -> bool:
        if predicate is None:

            def predicate(v: _T) -> bool:
                return bool(v)

        async for item in self:
            if not predicate(item):
                return False
        return True

    @property
    def is_completed(self) -> bool:
        return self._completed

    @property
    def error(self) -> Exception | None:
        return self._error

    @property
    def items_count(self) -> int:
        return len(self._items)
