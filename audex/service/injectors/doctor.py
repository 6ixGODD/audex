from __future__ import annotations

from audex.config import Config
from audex.lib.recorder import AudioRecorder
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.vp import VPRepository
from audex.lib.session import SessionManager
from audex.lib.vpr import VPR
from audex.service.doctor import DoctorService


def make_doctor_service(
    sm: SessionManager,
    config: Config,
    doctor_repo: DoctorRepository,
    vp_repo: VPRepository,
    vpr: VPR,
    recorder: AudioRecorder,
) -> DoctorService:
    pass
