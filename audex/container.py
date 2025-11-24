from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.applications.container import ApplicationContainer
from audex.injectors.config import config
from audex.injectors.lifespan import lifespan
from audex.lib.injectors.container import InfrastructureContainer
from audex.lib.repos.container import RepositoryContainer
from audex.service.injectors.container import ServiceContainer


class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Callable(config)

    # Containers
    infrastructure = providers.Container(InfrastructureContainer, config=config)
    repository = providers.Container(RepositoryContainer, sqlite=infrastructure.sqlite)
    service = providers.Container(
        ServiceContainer,
        config=config,
        infrastructure=infrastructure,
        repository=repository,
    )

    # Lifespan
    lifespan = providers.Singleton(
        lifespan,
        config,
        infrastructure.cache,
        infrastructure.sqlite,
        infrastructure.vpr,
        infrastructure.recorder,
        infrastructure.transcription,
    )

    # Application
    app = providers.Container(
        ApplicationContainer,
        config=config,
        lifespan=lifespan,
        infrastructure=infrastructure,
        service=service,
    )
