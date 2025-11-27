from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.config import Config
from audex.lib.injectors.cache import make_cache
from audex.lib.injectors.exporter import make_exporter
from audex.lib.injectors.recorder import make_recorder
from audex.lib.injectors.server import make_server
from audex.lib.injectors.session import make_session_manager
from audex.lib.injectors.sqlite import make_sqlite
from audex.lib.injectors.store import make_store
from audex.lib.injectors.transcription import make_transcription
from audex.lib.injectors.usb import make_usb_manager
from audex.lib.injectors.vpr import make_vpr
from audex.lib.injectors.wifi import make_wifi_manager
from audex.lib.repos.container import RepositoryContainer


class InfrastructureContainer(containers.DeclarativeContainer):
    # Dependencies
    config = providers.Dependency(instance_of=Config)

    # Components
    session_manager = providers.Singleton(make_session_manager, config=config)
    cache = providers.Singleton(make_cache, config=config)
    usb = providers.Singleton(make_usb_manager)
    wifi = providers.Singleton(make_wifi_manager)
    sqlite = providers.Singleton(make_sqlite, config=config)
    store = providers.Singleton(make_store, config=config)
    vpr = providers.Singleton(make_vpr, config=config)
    recorder = providers.Singleton(make_recorder, config=config, store=store)
    transcription = providers.Singleton(make_transcription, config=config)
    repository = providers.Container(RepositoryContainer, sqlite=sqlite)
    exporter = providers.Factory(
        make_exporter,
        session_repo=repository.session,
        segment_repo=repository.segment,
        utterance_repo=repository.utterance,
        store=store,
    )
    server = providers.Factory(
        make_server,
        doctor_repo=repository.doctor,
        exporter=exporter,
    )
