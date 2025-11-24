from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.lib.database.sqlite import SQLite
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.segment import SegmentRepository
from audex.lib.repos.session import SessionRepository
from audex.lib.repos.utterance import UtteranceRepository
from audex.lib.repos.vp import VPRepository


class RepositoryContainer(containers.DeclarativeContainer):
    # Dependencies
    sqlite = providers.Dependency(instance_of=SQLite)

    # Components
    doctor = providers.Factory(DoctorRepository, sqlite=sqlite)
    segment = providers.Factory(SegmentRepository, sqlite=sqlite)
    session = providers.Factory(SessionRepository, sqlite=sqlite)
    utterance = providers.Factory(UtteranceRepository, sqlite=sqlite)
    vp = providers.Factory(VPRepository, sqlite=sqlite)
