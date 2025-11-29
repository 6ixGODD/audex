from __future__ import annotations

from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field


class SQLiteConfig(BaseModel):
    uri: str = Field(
        default="sqlite+aiosqlite:///./audex.db",
        description="SQLite database URI.",
        windows_default="sqlite+aiosqlite:///C:/ProgramData/Audex/audex.db",
        linux_default="sqlite+aiosqlite:////var/lib/audex/audex.db",
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

    create_all: bool = Field(
        default=True,
        description="Whether to create all tables on initialization.",
    )
