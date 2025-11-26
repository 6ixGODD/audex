from __future__ import annotations

from audex.lib.cache import KVCache
from audex.lib.exporter import Exporter
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.server import Server
from audex.lib.session import SessionManager
from audex.lib.usb import USBManager
from audex.service.export import ExportService


def make_export_service(
    session_manager: SessionManager,
    cache: KVCache,
    doctor_repo: DoctorRepository,
    usb: USBManager,
    exporter: Exporter,
    server: Server,
) -> ExportService:
    return ExportService(
        session_manager=session_manager,
        cache=cache,
        doctor_repo=doctor_repo,
        usb=usb,
        exporter=exporter,
        server=server,
    )
