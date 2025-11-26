from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.lib.exporter import Exporter
    from audex.lib.repos.doctor import DoctorRepository
    from audex.lib.server import Server


def make_server(
    doctor_repo: DoctorRepository,
    exporter: Exporter,
) -> Server:
    from audex.lib.server import Server

    return Server(doctor_repo=doctor_repo, exporter=exporter)
