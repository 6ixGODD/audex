from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.injectors.config import config
from audex.injectors.lifespan import lifespan
from audex.lib.injectors.container import InfrastructureContainer
from audex.service.injectors.container import ServiceContainer
from audex.view.container import ViewContainer


class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Callable(config)

    # Containers
    infrastructure = providers.Container(InfrastructureContainer, config=config)
    service = providers.Container(
        ServiceContainer,
        config=config,
        infrastructure=infrastructure,
        repository=infrastructure.repository,
    )

    # Lifespan
    lifespan = providers.Singleton(
        lifespan,
        config,
        infrastructure.session_manager,
        infrastructure.wifi,
        infrastructure.cache,
        infrastructure.sqlite,
        infrastructure.vpr,
        infrastructure.recorder,
        infrastructure.transcription,
    )

    # Views
    views = providers.Container(ViewContainer, config=config, service=service, lifespan=lifespan)
