from __future__ import annotations

import typing as t

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from audex.config.core import CoreConfig
from audex.config.infrastructure import InfrastructureConfig
from audex.config.provider import ProviderConfig
from audex.helper.mixin import ContextMixin
from audex.helper.settings import Settings


class Config(ContextMixin, Settings):
    model_config: t.ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="PROTOTYPEX__",
        validate_default=False,
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    core: CoreConfig = Field(
        default_factory=CoreConfig,
        description="Core configuration settings.",
    )
    provider: ProviderConfig = Field(
        default_factory=ProviderConfig,
        description="Provider configuration settings.",
    )
    infrastructure: InfrastructureConfig = Field(
        default_factory=InfrastructureConfig,
        description="Infrastructure configuration settings.",
    )

    def init(self) -> None:
        self.core.logging.init()


config = None  # type: t.Optional[Config]


def build_config() -> Config:
    global config
    if config is None:
        config = Config()
    return config


def setconfig(cfg: Config, /) -> None:
    global config
    config = cfg


def getconfig() -> Config:
    global config
    if config is None:
        raise RuntimeError(
            "Configuration has not been initialized. Please call `build_config()` or `setconfig()` before accessing the configuration."
        )
    return config
