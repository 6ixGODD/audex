from __future__ import annotations

from audex.config import Config
from audex.lib.cache import KVCache
from audex.lib.recorder import AudioRecorder
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.segment import SegmentRepository
from audex.lib.repos.session import SessionRepository
from audex.lib.repos.utterance import UtteranceRepository
from audex.lib.repos.vp import VPRepository
from audex.lib.session import SessionManager
from audex.lib.transcription import Transcription
from audex.lib.vpr import VPR
from audex.service.session import SessionService
from audex.service.session import SessionServiceConfig


def make_session_service(
    session_manager: SessionManager,
    cache: KVCache,
    config: Config,
    doctor_repo: DoctorRepository,
    session_repo: SessionRepository,
    segment_repo: SegmentRepository,
    utterance_repo: UtteranceRepository,
    vp_repo: VPRepository,
    vpr: VPR,
    transcription: Transcription,
    recorder: AudioRecorder,
) -> SessionService:
    return SessionService(
        session_manager=session_manager,
        cache=cache,
        config=SessionServiceConfig(
            audio_key_prefix=config.core.audio.key_prefix,
            segment_buffer_ms=config.core.audio.segment_buffer,
            vpr_sr=config.core.audio.vpr_sample_rate,
            vpr_threshold=config.core.audio.vpr_threshold,
        ),
        doctor_repo=doctor_repo,
        session_repo=session_repo,
        segment_repo=segment_repo,
        utterance_repo=utterance_repo,
        vp_repo=vp_repo,
        vpr=vpr,
        transcription=transcription,
        recorder=recorder,
    )
