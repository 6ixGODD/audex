from __future__ import annotations

import typing as t

from pydantic import Field

from audex.helper.settings import BaseModel


class SQLiteConfig(BaseModel):
    uri: str = Field(
        default="sqlite:///audex.db",
        description="SQLite database URI.",
    )
    echo: bool = Field(
        default=False,
        description="Enable SQL query logging for debugging purposes.",
    )
    pool_size: int = Field(
        default=20,
        description="The size of the database connection pool.",
    )
    max_overflow: int = Field(
        default=10,
        description="The maximum overflow size of the connection pool.",
    )
    pool_timeout: float = Field(
        default=30.0,
        description="The timeout in seconds to wait for a connection from the pool.",
    )
    pool_recycle: int = Field(
        default=3600,
        description="The number of seconds after which a connection is automatically recycled.",
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Enable connection health checks before using a connection from the pool.",
    )


class DatabaseConfig(BaseModel):
    provider: t.Literal["sqlite"] = Field(
        default="sqlite",
        description="Database provider type. Currently only 'sqlite' is supported.",
    )

    sqlite: SQLiteConfig = Field(
        default_factory=SQLiteConfig,
        description="Configuration settings for SQLite database.",
    )
