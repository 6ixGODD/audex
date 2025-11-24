from __future__ import annotations

from dependency_injector import containers
from dependency_injector import providers

from audex.config import Config
from audex.service.injectors.doctor import make_doctor_service
from audex.service.injectors.session import make_session_service


class ServiceContainer(containers.DeclarativeContainer):
    # Dependencies
    config = providers.Dependency(instance_of=Config)
    infrastructure = providers.DependenciesContainer()
    repository = providers.DependenciesContainer()

    # Components
    doctor = providers.Factory(
        make_doctor_service,
        sm=infrastructure.sm,
        config=config,
        doctor_repo=repository.doctor,
        vp_repo=repository.vp,
        vpr=infrastructure.vpr,
        recorder=infrastructure.recorder,
    )

    session = providers.Factory(
        make_session_service,
        sm=infrastructure.sm,
        config=config,
        session_repo=repository.session,
        segment_repo=repository.segment,
        utterance_repo=repository.utterance,
        vp_repo=repository.vp,
        vpr=infrastructure.vpr,
        transcription=infrastructure.transcription,
        recorder=infrastructure.recorder,
    )
