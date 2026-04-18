from __future__ import annotations

from audex.config.core.app import AppConfig
from audex.config.core.audio import AudioConfig
from audex.config.core.logging import LoggingConfig
from audex.config.core.session import SessionConfig
from audex.config.core.ui import UIConfig
from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field


class CoreConfig(BaseModel):
    app: AppConfig = Field(
        default_factory=AppConfig,
        description="Application specific configuration",
    )

    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )

    audio: AudioConfig = Field(
        default_factory=AudioConfig,
        description="Audio processing configuration",
    )

    session: SessionConfig = Field(
        default_factory=SessionConfig,
        description="Session management configuration",
    )

    ui: UIConfig = Field(
        default_factory=UIConfig,
        description="UI behaviour configuration",
    )
