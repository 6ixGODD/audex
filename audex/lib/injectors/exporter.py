from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.lib.exporter import Exporter
    from audex.lib.repos.segment import SegmentRepository
    from audex.lib.repos.session import SessionRepository
    from audex.lib.repos.utterance import UtteranceRepository
    from audex.lib.store import Store


def make_exporter(
    session_repo: SessionRepository,
    segment_repo: SegmentRepository,
    utterance_repo: UtteranceRepository,
    store: Store,
) -> Exporter:
    from audex.lib.exporter import Exporter

    return Exporter(
        session_repo=session_repo,
        segment_repo=segment_repo,
        utterance_repo=utterance_repo,
        store=store,
    )
