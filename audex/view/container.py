from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.config import Config
from audex.lifespan import LifeSpan
from audex.view import View


class ViewContainer(containers.DeclarativeContainer):
    # Dependencies
    config = providers.Dependency(instance_of=Config)
    service = providers.DependenciesContainer()
    lifespan = providers.Dependency(instance_of=LifeSpan)

    view = providers.Singleton(View, lifespan=lifespan, config=config)
