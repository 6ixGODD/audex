from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.applications import AudexApplication
from audex.applications.api import AudexAPI
from audex.config import Config
from audex.lifespan import LifeSpan


class ApplicationContainer(containers.DeclarativeContainer):
    config = providers.Dependency(instance_of=Config)
    lifespan = providers.Dependency(instance_of=LifeSpan)
    infrastructure = providers.DependenciesContainer()
    service = providers.DependenciesContainer()

    api = providers.Singleton(
        AudexAPI,
        session_manager=infrastructure.session_manager,
        doctor_service=service.doctor,
        session_service=service.session,
    )

    app = providers.Singleton(
        AudexApplication,
        api=api,
        lifespan=lifespan,
        width=providers.Callable(lambda cfg: cfg.gui.width, config),
        height=providers.Callable(lambda cfg: cfg.gui.height, config),
        fullscreen=providers.Callable(lambda cfg: cfg.gui.fullscreen, config),
    )
