from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.injectors.config import config
from audex.injectors.infrastructure import InfrastructureContainer
from audex.injectors.lifespan import lifespan


class Container(containers.DeclarativeContainer):
    config = providers.Callable(config)
    infrastructure = providers.Container(InfrastructureContainer, config=config)
    lifespan = providers.Singleton(lifespan, config, infrastructure.cache)
