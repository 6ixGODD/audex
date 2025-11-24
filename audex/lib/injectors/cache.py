from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.config import Config
    from audex.lib.cache import KeyBuilder
    from audex.lib.cache import KVCache


def make_cache(config: Config) -> KVCache:
    key_builder = KeyBuilder(
        split_char=config.infrastructure.cache.split_char,
        prefix=config.infrastructure.cache.prefix,
    )
    if config.infrastructure.cache.provider == "inmemory":
        from audex.lib.cache.inmemory import InmemoryCache

        return InmemoryCache(
            key_builder=key_builder,
            cache_type=config.infrastructure.cache.inmemory.cache_type,
            maxsize=config.infrastructure.cache.inmemory.max_size,
            default_ttl=config.infrastructure.cache.inmemory.default_ttl,
            negative_ttl=config.infrastructure.cache.inmemory.negative_ttl,
        )

    return NotImplemented
