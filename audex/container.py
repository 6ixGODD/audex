from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.injectors.config import config
from audex.injectors.infrastructure import InfrastructureContainer
from audex.injectors.lifespan import lifespan
from audex.injectors.repos import RepositoryContainer
from audex.injectors.service import ServiceContainer


class Container(containers.DeclarativeContainer):
    config = providers.Callable(config)
    infrastructure = providers.Container(
        InfrastructureContainer,
        config=config,
    )
    repository = providers.Container(
        RepositoryContainer,
        sqlite=infrastructure.sqlite,
    )
    service = providers.Container(
        ServiceContainer,
        config=config,
        infrastructure=infrastructure,
        repository=repository,
    )
    lifespan = providers.Singleton(lifespan, config, infrastructure.cache)
