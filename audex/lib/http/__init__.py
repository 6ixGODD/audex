from __future__ import annotations

from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.repos.segment import SegmentRepository
from audex.lib.repos.session import SessionRepository
from audex.lib.repos.utterance import UtteranceRepository
from audex.lib.store import Store


class HTTPServer(AsyncContextMixin, LoggingMixin):
    __logtag__ = "audex.lib.http"

    def __init__(
        self,
        doctor_repo: DoctorRepository,
        segment_repo: SegmentRepository,
        session_repo: SessionRepository,
        utterance_repo: UtteranceRepository,
        store: Store,
    ):
        super().__init__()
        self.doctor_repo = doctor_repo
        self.segment_repo = segment_repo
        self.session_repo = session_repo
        self.utterance_repo = utterance_repo
        self.store = store
