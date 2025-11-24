from __future__ import annotations

import asyncio
import collections
import time
import typing as t

import cachetools

from audex.lib.cache import CACHE_MISS
from audex.lib.cache import EMPTY
from audex.lib.cache import VT
from audex.lib.cache import CacheMiss
from audex.lib.cache import Empty
from audex.lib.cache import KeyBuilder
from audex.lib.cache import KVCache


class TTLEntry:
    """Wrapper for cache entries with TTL information."""

    __slots__ = ("expire_at", "value")

    def __init__(self, value: t.Any, ttl: int | None = None):
        self.value = value
        self.expire_at = time.time() + ttl if ttl is not None else None

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expire_at is None:
            return False
        return time.time() > self.expire_at

    def get_ttl(self) -> int | None:
        """Get remaining TTL in seconds."""
        if self.expire_at is None:
            return None
        remaining = int(self.expire_at - time.time())
        return max(0, remaining)


class InmemoryCache(KVCache):
    __logtag__ = "audex.lib.cache.inmemory"

    def __init__(
        self,
        *,
        key_builder: KeyBuilder,
        cache_type: t.Literal["lru", "lfu", "ttl", "fifo"] = "lru",
        maxsize: int = 1000,
        default_ttl: int = 300,
        negative_ttl: int = 60,
    ) -> None:
        """Initialize InmemoryCache.

        Args:
            key_builder: KeyBuilder instance for building cache keys
            cache_type: Type of cache strategy ('lru', 'lfu', 'ttl', 'fifo')
            maxsize: Maximum number of items in cache
            default_ttl: Default TTL in seconds for cache entries
            negative_ttl: TTL in seconds for negative cache entries
        """
        super().__init__()
        self._key_builder = key_builder
        self.cache_type = cache_type
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self.negative_ttl = negative_ttl
        self.logger.info("Initializing Cachetools cache")

        # Thread lock for thread-safe operations (async lock)
        self._lock = asyncio.Lock()

        # Initialize the appropriate cache type
        if cache_type == "lru":
            self._cache: t.MutableMapping[str, TTLEntry] = cachetools.LRUCache(maxsize=maxsize)
            self.logger.info(f"Initialized LRU cache with maxsize={maxsize}")
        elif cache_type == "lfu":
            self._cache: t.MutableMapping[str, TTLEntry] = cachetools.LFUCache(maxsize=maxsize)
            self.logger.info(f"Initialized LFU cache with maxsize={maxsize}")
        elif cache_type == "ttl":
            cache_ttl = default_ttl
            self._cache: t.MutableMapping[str, TTLEntry] = cachetools.TTLCache(
                maxsize=maxsize, ttl=cache_ttl
            )
            self.logger.info(f"Initialized TTL cache with maxsize={maxsize}, ttl={cache_ttl}")
        elif cache_type == "fifo":
            # Cachetools doesn't have built-in FIFO, use OrderedDict wrapper
            self._cache: t.MutableMapping[str, TTLEntry] = collections.OrderedDict()
            self._maxsize = maxsize
            self.logger.info(f"Initialized FIFO cache with maxsize={maxsize}")
        else:
            # Default to LRU
            self._cache: t.MutableMapping[str, TTLEntry] = cachetools.LRUCache(maxsize=maxsize)
            self.logger.warning(f"Unknown cache type '{cache_type}', defaulting to LRU")
            self.cache_type = "lru"

        self.logger.info(
            f"Cachetools cache initialized with type={self.cache_type}, maxsize={maxsize}",
            cache_type=self.cache_type,
            maxsize=maxsize,
        )

    @property
    def key_builder(self) -> KeyBuilder:
        """Get the key builder instance."""
        return self._key_builder

    async def _evict_if_needed(self) -> None:
        """Evict the oldest entry if FIFO cache is at capacity."""
        if (
            self.cache_type == "fifo"
            and len(self._cache) >= self._maxsize
            and isinstance(self._cache, collections.OrderedDict)
        ):
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self.logger.debug(f"Evicted oldest entry: {oldest_key}")

    async def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        if self.cache_type == "ttl":
            # TTLCache handles expiration automatically
            return

        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            try:
                del self._cache[key]
                self.logger.debug(f"Removed expired entry: {key}")
            except KeyError:
                pass

    async def set_negative(self, key: str, /) -> None:
        """Store cache miss marker to prevent cache penetration."""
        async with self._lock:
            try:
                await self._evict_if_needed()
                entry = TTLEntry(CACHE_MISS, self.negative_ttl)
                self._cache[key] = entry
                self.logger.debug(f"Set negative cache for key: {key}")
            except Exception as e:
                self.logger.warning(f"Failed to set negative cache for key {key}: {e}")

    async def get_item(self, key: str) -> VT | Empty:
        async with self._lock:
            try:
                await self._cleanup_expired()
                entry = self._cache.get(key)

                if entry is None:
                    self.logger.debug(f"Cache miss for key: {key}")
                    return EMPTY

                if entry.is_expired():
                    del self._cache[key]
                    self.logger.debug(f"Entry expired for key: {key}")
                    return EMPTY

                if isinstance(entry.value, CacheMiss):
                    self.logger.debug(f"Found negative cache for key: {key}")
                    return EMPTY

                self.logger.debug(f"Cache hit for key: {key}")
                return entry.value
            except Exception as e:
                self.logger.error(f"Error when getting key {key}: {e}")
                return EMPTY

    async def set_item(self, key: str, value: VT) -> None:
        async with self._lock:
            try:
                await self._evict_if_needed()
                entry = TTLEntry(value, self.default_ttl)
                self._cache[key] = entry
                self.logger.debug(f"Successfully cached key: {key}")
            except Exception as e:
                self.logger.error(f"Failed to set cache for key {key}: {e}")

    async def del_item(self, key: str) -> None:
        async with self._lock:
            try:
                if key not in self._cache:
                    self.logger.debug(f"Key not found for deletion: {key}")
                    raise KeyError(key)
                del self._cache[key]
                self.logger.debug(f"Successfully deleted key: {key}")
            except KeyError:
                raise
            except Exception as e:
                self.logger.error(f"Error when deleting key {key}: {e}")
                raise KeyError(key) from e

    async def iter_keys(self) -> t.AsyncIterator[str]:
        async with self._lock:
            try:
                await self._cleanup_expired()
                count = 0
                keys_snapshot = list(self._cache.keys())

                for key in keys_snapshot:
                    if self.key_builder.validate(key):
                        yield key
                        count += 1

                self.logger.debug(f"Iterated over {count} cache keys")
            except Exception as e:
                self.logger.error(f"Error during iteration: {e}")
                return

    async def len(self) -> int:
        async with self._lock:
            try:
                await self._cleanup_expired()
                count = sum(1 for key in self._cache if self.key_builder.validate(key))
                self.logger.debug(f"Cache contains {count} keys")
                return count
            except Exception as e:
                self.logger.error(f"Error when counting keys: {e}")
                return 0

    async def contains(self, key: str) -> bool:
        if not self.key_builder.validate(key):
            return False
        async with self._lock:
            try:
                await self._cleanup_expired()
                if key not in self._cache:
                    return False

                entry = self._cache[key]
                if entry.is_expired():
                    del self._cache[key]
                    return False

                self.logger.debug(f"Key existence check for {key}: True")
                return True
            except Exception as e:
                self.logger.error(f"Error when checking key existence {key}: {e}")
                return False

    async def keys(self) -> list[str]:
        """Return a list of cache keys."""
        result = []
        async for key in self.iter_keys():
            result.append(key)
        return result

    async def get(self, key: str, default: VT | None = None, /) -> VT | None:
        """Get value from cache, return default if not found."""
        result = await self.get_item(key)
        if isinstance(result, Empty):
            return default
        return result

    async def setdefault(self, key: str, default: VT | None = None, /) -> VT | None:
        """Get value or set and return default if key doesn't exist."""
        async with self._lock:
            try:
                await self._cleanup_expired()
                entry = self._cache.get(key)

                if entry is not None and not entry.is_expired():
                    if isinstance(entry.value, CacheMiss):
                        self.logger.debug(f"Key {key} in negative cache")
                        return default
                    self.logger.debug(f"Key {key} exists, returning cached value")
                    return entry.value

                # Key doesn't exist or is expired
                if entry is not None and entry.is_expired():
                    del self._cache[key]

                if default is not None:
                    await self._evict_if_needed()
                    new_entry = TTLEntry(default, self.default_ttl)
                    self._cache[key] = new_entry
                    self.logger.debug(f"Set default value for key: {key}")
                    return default

                await self._evict_if_needed()
                neg_entry = TTLEntry(CACHE_MISS, self.negative_ttl)
                self._cache[key] = neg_entry
                self.logger.debug(f"Set negative cache for key: {key}")
                return None

            except Exception as e:
                self.logger.error(f"Error in setdefault for key {key}: {e}")
                return default

    async def clear(self) -> None:
        """Clear all cache entries with the configured prefix."""
        async with self._lock:
            try:
                keys_to_delete = [key for key in self._cache if self.key_builder.validate(key)]

                for key in keys_to_delete:
                    del self._cache[key]

                self.logger.info(f"Cleared {len(keys_to_delete)} cache entries")
            except Exception as e:
                self.logger.error(f"Failed to clear cache: {e}")

    async def pop(self, key: str, default: VT | None = None, /) -> VT | None:
        """Remove and return value, or return default if not found."""
        async with self._lock:
            try:
                await self._cleanup_expired()
                entry = self._cache.get(key)

                if entry is not None and not entry.is_expired():
                    del self._cache[key]
                    if isinstance(entry.value, CacheMiss):
                        return default
                    self.logger.debug(f"Successfully popped key: {key}")
                    return entry.value

                self.logger.debug(f"Key not found for pop operation: {key}")
                return default
            except Exception as e:
                self.logger.error(f"Error when popping key {key}: {e}")
                return default

    async def popitem(self) -> tuple[str, VT]:
        """Remove and return an arbitrary (key, value) pair."""
        async with self._lock:
            try:
                await self._cleanup_expired()

                for key in list(self._cache.keys()):
                    if not self.key_builder.validate(key):
                        continue

                    entry = self._cache.get(key)
                    if entry is not None and not entry.is_expired():
                        del self._cache[key]
                        if not isinstance(entry.value, CacheMiss):
                            self.logger.debug(f"Successfully popped item: {key}")
                            return key, entry.value

                self.logger.debug("No items to pop")
                raise KeyError("popitem(): cache is empty")
            except KeyError:
                raise
            except Exception as e:
                self.logger.error(f"Error during popitem: {e}")
                raise KeyError(f"popitem() failed: {e}") from e

    async def set(self, key: str, value: VT, /) -> None:
        """Set a key-value pair (alias for set_item)."""
        await self.set_item(key, value)

    async def setx(self, key: str, value: VT, /, ttl: int | None = None) -> None:
        """Set a key-value pair with optional TTL."""
        async with self._lock:
            try:
                await self._evict_if_needed()
                entry = TTLEntry(value, ttl)
                self._cache[key] = entry

                if ttl is not None:
                    self.logger.debug(f"Set key {key} with TTL {ttl}")
                else:
                    self.logger.debug(f"Set key {key} without TTL")
            except Exception as e:
                self.logger.error(f"Failed to setx for key {key}: {e}")

    async def ttl(self, key: str, /) -> int | None:
        """Get TTL for a key."""
        async with self._lock:
            try:
                entry = self._cache.get(key)

                if entry is None:
                    self.logger.debug(f"Key {key} does not exist")
                    return None

                if entry.is_expired():
                    del self._cache[key]
                    self.logger.debug(f"Key {key} has expired")
                    return None

                ttl_value = entry.get_ttl()
                if ttl_value is None:
                    self.logger.debug(f"Key {key} exists without expiration")
                else:
                    self.logger.debug(f"Key {key} TTL: {ttl_value}")

                return ttl_value
            except Exception as e:
                self.logger.error(f"Error when getting TTL for key {key}: {e}")
                return None

    async def expire(self, key: str, /, ttl: int | None = None) -> None:
        """Set or remove expiration for a key."""
        async with self._lock:
            try:
                entry = self._cache.get(key)

                if entry is None:
                    self.logger.warning(f"Cannot set expiration for non-existent key: {key}")
                    return

                if entry.is_expired():
                    del self._cache[key]
                    self.logger.warning(f"Key {key} has already expired")
                    return

                # Create new entry with updated TTL
                new_entry = TTLEntry(entry.value, ttl)
                self._cache[key] = new_entry

                if ttl is not None:
                    self.logger.debug(f"Set expiration for key {key}: {ttl} seconds")
                else:
                    self.logger.debug(f"Removed expiration for key: {key}")
            except Exception as e:
                self.logger.error(f"Error when setting expiration for key {key}: {e}")

    async def incr(self, key: str, /, amount: int = 1) -> int:
        """Increment a key's value."""
        async with self._lock:
            try:
                await self._cleanup_expired()
                entry = self._cache.get(key)

                if entry is None or entry.is_expired():
                    # Initialize to amount if key doesn't exist
                    new_value = amount
                    await self._evict_if_needed()
                    new_entry = TTLEntry(new_value, self.default_ttl)
                    self._cache[key] = new_entry
                    self.logger.debug(f"Initialized and incremented key {key} to {new_value}")
                    return new_value

                if not isinstance(entry.value, int):
                    self.logger.error(f"Cannot increment non-integer value for key {key}")
                    raise ValueError(f"Value at key {key} is not an integer")

                new_value = entry.value + amount
                # Preserve existing TTL
                existing_ttl = entry.get_ttl()
                new_entry = TTLEntry(new_value, existing_ttl)
                self._cache[key] = new_entry

                self.logger.debug(f"Incremented key {key} by {amount}, result: {new_value}")
                return new_value
            except Exception as e:
                self.logger.error(f"Error when incrementing key {key}: {e}")
                return 0

    async def decr(self, key: str, /, amount: int = 1) -> int:
        """Decrement a key's value."""
        return await self.incr(key, -amount)

    async def values(self) -> list[VT]:
        """Return all cache values."""
        async with self._lock:
            try:
                await self._cleanup_expired()
                values = []
                for key, entry in self._cache.items():
                    if not self.key_builder.validate(key):
                        continue
                    if entry.is_expired():
                        continue
                    if isinstance(entry.value, CacheMiss):
                        continue
                    values.append(entry.value)
                return values
            except Exception as e:
                self.logger.error(f"Error when getting values: {e}")
                return []

    async def items(self) -> list[tuple[str, VT]]:
        """Return all cache items as (key, value) pairs."""
        async with self._lock:
            try:
                await self._cleanup_expired()
                items = []
                for key, entry in self._cache.items():
                    if not self.key_builder.validate(key):
                        continue
                    if entry.is_expired():
                        continue
                    if isinstance(entry.value, CacheMiss):
                        continue
                    items.append((key, entry.value))
                return items
            except Exception as e:
                self.logger.error(f"Error when getting items: {e}")
                return []

    async def init(self) -> None:
        """Initialize cache resources if needed."""
        self.logger.info("InmemoryCache initialized")

    async def close(self) -> None:
        """Close cache and cleanup resources."""
        async with self._lock:
            try:
                self._cache.clear()
                self.logger.info("Cachetools cache closed and cleared")
            except Exception as e:
                self.logger.warning(f"Error while closing cache: {e}")
