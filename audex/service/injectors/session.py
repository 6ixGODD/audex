from __future__ import annotations

from audex.config import Config
from audex.lib.recorder import AudioRecorder
from audex.lib.repos.segment import SegmentRepository
from audex.lib.repos.session import SessionRepository
from audex.lib.repos.utterance import UtteranceRepository
from audex.lib.repos.vp import VPRepository
from audex.lib.session import SessionManager
from audex.lib.transcription import Transcription
from audex.lib.vpr import VPR
from audex.service.session import SessionService


def make_session_service(
    sm: SessionManager,
    config: Config,
    session_repo: SessionRepository,
    segment_repo: SegmentRepository,
    utterance_repo: UtteranceRepository,
    vp_repo: VPRepository,
    vpr: VPR,
    transcription: Transcription,
    recorder: AudioRecorder,
) -> SessionService:
    pass
