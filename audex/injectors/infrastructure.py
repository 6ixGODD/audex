from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.config import Config
from audex.lib.injectors.cache import make_cache
from audex.lib.injectors.recorder import make_recorder
from audex.lib.injectors.session import make_session_manager
from audex.lib.injectors.sqlite import make_sqlite
from audex.lib.injectors.store import make_store
from audex.lib.injectors.transcription import make_transcription
from audex.lib.injectors.vpr import make_vpr


class InfrastructureContainer(containers.DeclarativeContainer):
    # Dependencies
    config = providers.Dependency(instance_of=Config)

    # Components
    sm = providers.Singleton(make_session_manager, config=config)
    cache = providers.Singleton(make_cache, config=config)
    sqlite = providers.Singleton(make_sqlite, config=config)
    store = providers.Singleton(make_store, config=config)
    vpr = providers.Singleton(make_vpr, config=config)
    recorder = providers.Singleton(make_recorder, config=config, store=store)
    transcription = providers.Singleton(make_transcription, config=config)
