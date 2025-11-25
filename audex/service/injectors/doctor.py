from __future__ import annotations

from audex.config import Config
from audex.lib.cache import KVCache
from audex.lib.recorder import AudioRecorder
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.vp import VPRepository
from audex.lib.session import SessionManager
from audex.lib.vpr import VPR
from audex.service.doctor import DoctorService
from audex.service.doctor import DoctorServiceConfig


def make_doctor_service(
    session_manager: SessionManager,
    cache: KVCache,
    config: Config,
    doctor_repo: DoctorRepository,
    vp_repo: VPRepository,
    vpr: VPR,
    recorder: AudioRecorder,
) -> DoctorService:
    return DoctorService(
        session_manager=session_manager,
        cache=cache,
        config=DoctorServiceConfig(
            vpr_sr=config.core.audio.vpr_sample_rate,
            vpr_text_content=config.core.audio.vpr_text_content,
        ),
        doctor_repo=doctor_repo,
        vp_repo=vp_repo,
        vpr=vpr,
        recorder=recorder,
    )
