from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.config import Config
from audex.lib.injectors.cache import make_cache


class InfrastructureContainer(containers.DeclarativeContainer):
    # Dependencies
    config = providers.Dependency(instance_of=Config)

    # Components
    cache = providers.Singleton(make_cache, config=config)
