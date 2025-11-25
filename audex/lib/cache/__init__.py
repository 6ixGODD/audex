from __future__ import annotations

import abc
import typing as t

from audex import __title__
from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin


class Empty:
    """Sentinel type representing an empty/missing value.

    Used to distinguish between None (a valid value) and a truly missing value.
    Always evaluates to False in boolean context.

    Example:
        ```python
        async def get_value(key: str) -> str | Empty:
            if key not in data:
                return EMPTY
            return data[key]


        value = await get_value("missing")
        if value is EMPTY:
            print("Value not found")
        ```
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<EMPTY>"

    __str__ = __repr__

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Empty)

    def __hash__(self) -> int:
        return hash("<EMPTY>")


EMPTY = Empty()


class Placeholder:
    """Sentinel type representing a placeholder value.

    Used to mark positions where a value will be provided later. Always
    evaluates to True in boolean context.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<PLACEHOLDER>"

    __str__ = __repr__

    def __bool__(self) -> bool:
        return True

    def __getstate__(self) -> tuple[()]:
        return ()

    def __setstate__(self, state: tuple[()]) -> None:
        pass

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Placeholder)

    def __hash__(self) -> int:
        return hash("<PLACEHOLDER>")


PLACEHOLDER = Placeholder()


class CacheMiss:
    """Sentinel type representing a cache miss.

    Used to distinguish between cached None values and keys that don't
    exist. Always evaluates to False in boolean context.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<CACHE_MISS>"

    __str__ = __repr__

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CacheMiss)

    def __hash__(self) -> int:
        return hash("<CACHE_MISS>")

    def __getstate__(self) -> tuple[()]:
        return ()

    def __setstate__(self, state: tuple[()]) -> None:
        pass


CACHE_MISS = CacheMiss()


class Negative:
    """Sentinel type representing a negative cache entry.

    Used to mark keys that are known to be absent, preventing cache
    penetration. Always evaluates to False in boolean context.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<NEGATIVE>"

    __str__ = __repr__

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Negative)

    def __hash__(self) -> int:
        return hash("<NEGATIVE>")

    def __getstate__(self) -> tuple[()]:
        return ()

    def __setstate__(self, state: tuple[()]) -> None:
        pass


NEGATIVE = Negative()


class KeyBuilder:
    """Utility class for building cache keys with a consistent format.

    Provides methods to construct namespaced cache keys and validate key formats.

    Attributes:
        split_char: Character used to split parts of the key.
        prefix: Prefix to prepend to all keys.

    Args:
        split_char: Separator character for key parts. Defaults to ":".
        prefix: Namespace prefix for all keys. Defaults to normalized project title.

    Example:
        ```python
        builder = KeyBuilder(prefix="myapp")

        # Build keys
        user_key = builder.build("user", "123")  # "myapp:user:123"
        session_key = builder.build(
            "session", "abc"
        )  # "myapp:session:abc"

        # Validate keys
        builder.validate("myapp:user:123")  # True
        builder.validate("other:user:123")  # False
        ```
    """

    __slots__ = ("prefix", "split_char")

    def __init__(
        self,
        split_char: str = ":",
        prefix: str = __title__.lower().replace(" ", "_"),
    ) -> None:
        self.split_char = split_char
        self.prefix = prefix

    def build(self, *parts: str) -> str:
        """Build a cache key by joining the prefix and parts.

        Args:
            *parts: Parts to include in the key.

        Returns:
            The constructed cache key.
        """
        return self.split_char.join((self.prefix, *parts))

    def validate(self, key: str) -> bool:
        """Validate if a given key starts with the defined prefix.

        Args:
            key: The cache key to validate.

        Returns:
            True if the key starts with the prefix, False otherwise.
        """
        return key.startswith(self.prefix + self.split_char)

    def __repr__(self) -> str:
        return f"CACHE KEY BUILDER <{self.__class__.__name__} (prefix={self.prefix}, split_char={self.split_char})>"


T = t.TypeVar("T")
VT = t.TypeVar("VT")


class KVCache(LoggingMixin, AsyncContextMixin, abc.ABC):
    """Abstract base class for async key-value cache implementations.

    Provides an async dictionary-like interface for caching with support for TTL,
    atomic operations (incr/decr), and key validation. Implementations can
    use in-memory storage, Redis, or other backends.

    The cache supports:
    - Async dict operations (get, set, delete, etc.)
    - Time-to-live (TTL) for automatic expiration
    - Atomic increment/decrement operations
    - Key namespace management via KeyBuilder

    Example:
        ```python
        # Using a cache implementation
        cache = await make_cache(config, logger)

        # Basic operations
        await cache.set("user:123", {"name": "Alice"})
        user = await cache.get("user:123")

        # With TTL
        await cache.setx("session:abc", {"data": "..."}, ttl=3600)

        # Atomic operations
        await cache.incr("counter:visits")
        await cache.decr("counter:remaining", amount=5)
        ```
    """

    @property
    @abc.abstractmethod
    def key_builder(self) -> KeyBuilder:
        """Get the KeyBuilder instance used for constructing cache
        keys."""

    @abc.abstractmethod
    async def get_item(self, key: str) -> VT | Empty | Negative:
        """Retrieve an item from the cache by key."""

    @abc.abstractmethod
    async def set_item(self, key: str, value: VT) -> None:
        """Set an item in the cache with the specified key and value."""

    @abc.abstractmethod
    async def del_item(self, key: str) -> None:
        """Delete an item from the cache by key."""

    @abc.abstractmethod
    async def iter_keys(self) -> t.AsyncIterator[str]:
        """Return an async iterator over the keys in the cache."""

    @abc.abstractmethod
    async def len(self) -> int:
        """Return the number of items in the cache."""

    @abc.abstractmethod
    async def contains(self, key: str) -> bool:
        """Check if the cache contains a specific key."""

    @t.overload
    async def get(self, key: str, /) -> VT | None: ...
    @t.overload
    async def get(self, key: str, /, default: VT) -> VT: ...
    @t.overload
    async def get(self, key: str, /, default: T) -> VT | T: ...
    @t.overload
    async def get(self, key: str, /, default: None = None) -> VT | None: ...
    @abc.abstractmethod
    async def get(self, key: str, /, default: VT | T | None = None) -> VT | T | None:
        """Get an item from the cache, returning default if the key does
        not exist."""

    @t.overload
    async def setdefault(self, key: str, default: None = None, /) -> VT | None: ...
    @t.overload
    async def setdefault(self, key: str, default: VT, /) -> VT: ...
    @abc.abstractmethod
    async def setdefault(self, key: str, default: VT | None = None, /) -> VT | None:
        """Set a default value for a key if it does not exist in the
        cache."""

    @abc.abstractmethod
    async def clear(self) -> None:
        """Clear all items from the cache."""

    @t.overload
    async def pop(self, key: str, /) -> VT: ...
    @t.overload
    async def pop(self, key: str, /, default: VT) -> VT: ...
    @t.overload
    async def pop(self, key: str, /, default: T) -> VT | T: ...
    @t.overload
    async def pop(self, key: str, /, default: None = None) -> VT | None: ...
    @abc.abstractmethod
    async def pop(self, key: str, /, default: VT | T | None = None) -> VT | T:
        """Remove and return an item from the cache by key."""

    @abc.abstractmethod
    async def popitem(self) -> tuple[str, VT]:
        """Remove and return an arbitrary (key, value) pair from the
        cache."""

    @abc.abstractmethod
    async def set(self, key: str, value: VT) -> None:
        """Set an item in the cache with the specified key and value."""

    @abc.abstractmethod
    async def setx(self, key: str, value: VT, ttl: int | None = None) -> None:
        """Set an item in the cache with the specified key, value, and
        optional TTL.

        Args:
            key: Cache key.
            value: Value to store.
            ttl: Time-to-live in seconds. None means use default TTL.
        """

    @abc.abstractmethod
    async def set_negative(self, key: str, /) -> None:
        """Store cache miss marker to prevent cache penetration.

        Args:
            key: Cache key.
        """

    @abc.abstractmethod
    async def ttl(self, key: str) -> int | None:
        """Get the time-to-live (TTL) for a specific key in the cache.

        Args:
            key: Cache key.

        Returns:
            Remaining TTL in seconds, or None if no TTL is set.
        """

    @abc.abstractmethod
    async def expire(self, key: str, ttl: int | None = None) -> None:
        """Set the time-to-live (TTL) for a specific key in the cache.

        Args:
            key: Cache key.
            ttl: Time-to-live in seconds. None means use default TTL.
        """

    @abc.abstractmethod
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment the integer value of a key by the given amount.

        Args:
            key: Cache key.
            amount: Amount to increment by. Defaults to 1.

        Returns:
            The new value after incrementing.
        """

    @abc.abstractmethod
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement the integer value of a key by the given amount.

        Args:
            key: Cache key.
            amount: Amount to decrement by. Defaults to 1.

        Returns:
            The new value after decrementing.
        """

    @abc.abstractmethod
    async def keys(self) -> list[str]:
        """Return a list of cache keys."""

    @abc.abstractmethod
    async def values(self) -> list[VT]:
        """Return all cache values."""

    @abc.abstractmethod
    async def items(self) -> list[tuple[str, VT]]:
        """Return all cache items as (key, value) pairs."""

    def __repr__(self) -> str:
        return f"ASYNC KV CACHE <{self.__class__.__name__}>"
