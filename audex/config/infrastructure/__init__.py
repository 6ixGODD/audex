from __future__ import annotations

from pydantic import Field

from audex.config.infrastructure.cache import CacheConfig
from audex.config.infrastructure.database import SQLiteConfig
from audex.config.infrastructure.recorder import RecorderConfig
from audex.config.infrastructure.store import StoreConfig
from audex.helper.settings import BaseModel


class InfrastructureConfig(BaseModel):
    sqlite: SQLiteConfig = Field(
        default_factory=SQLiteConfig,
        description="SQLite configuration.",
    )

    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="Cache configuration.",
    )

    store: StoreConfig = Field(
        default_factory=StoreConfig,
        description="Store configuration.",
    )

    recorder: RecorderConfig = Field(
        default_factory=RecorderConfig,
        description="Recorder configuration.",
    )
