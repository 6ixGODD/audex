from __future__ import annotations

from pydantic import Field

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
