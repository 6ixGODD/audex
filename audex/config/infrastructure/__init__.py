from __future__ import annotations

from pydantic import Field

from audex.config.infrastructure.cache import CacheConfig
from audex.config.infrastructure.database import DatabaseConfig
from audex.helper.settings import BaseModel


class InfrastructureConfig(BaseModel):
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig,
        description="Database configuration.",
    )

    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="Cache configuration.",
    )
