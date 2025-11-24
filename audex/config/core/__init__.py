from __future__ import annotations

from pydantic import Field

from audex.config.core.audio import AudioConfig
from audex.config.core.logging import LoggingConfig
from audex.config.core.server import ServerConfig
from audex.helper.settings import BaseModel


class CoreConfig(BaseModel):
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )

    server: ServerConfig = Field(
        default_factory=ServerConfig,
        description="Server configuration",
    )

    audio: AudioConfig = Field(
        default_factory=AudioConfig,
        description="Audio processing configuration",
    )

    app_name: str = Field(
        default="Audex",
        description="The name of the application.",
    )

    session_ttl_minutes: int = Field(
        default=60,
        description="Time-to-live for user sessions in minutes.",
    )
