from __future__ import annotations

from audex.config import Config
from audex.lib.exporter import Exporter
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.server import Server
from audex.lib.server import ServerConfig


def make_server(
    config: Config,
    doctor_repo: DoctorRepository,
    exporter: Exporter,
) -> Server:
    return Server(
        config=ServerConfig(
            host=config.core.server.host,
            port=config.core.server.port,
        ),
        doctor_repo=doctor_repo,
        exporter=exporter,
    )
