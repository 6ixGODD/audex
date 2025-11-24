from __future__ import annotations

import typing as t

from pydantic import Field

from audex import __title__
from audex.helper.settings import BaseModel


class InmemoryCacheConfig(BaseModel):
    cache_type: t.Literal["lru", "lfu", "ttl", "fifo"] = Field(
        default="ttl",
        description="Type of in-memory cache algorithm to use.",
    )

    max_size: int = Field(
        default=1024,
        description="Maximum number of items to store in the cache.",
    )

    default_ttl: int = Field(
        default=300,
        description="Default time-to-live (TTL) for cache items in seconds.",
    )

    negative_ttl: int = Field(
        default=60,
        description="TTL for negative cache entries in seconds.",
    )


class CacheConfig(BaseModel):
    provider: t.Literal["inmemory"] = Field(
        default="inmemory",
        description="Type of cache backend to use.",
    )

    split_char: str = Field(
        default=":",
        description="Character used to split cache keys.",
    )

    prefix: str = Field(
        default=__title__.lower().replace(" ", "_"),
        description="Prefix for all cache keys.",
    )

    inmemory: InmemoryCacheConfig = Field(
        default_factory=InmemoryCacheConfig,
        description="Configuration for in-memory cache backend.",
    )
