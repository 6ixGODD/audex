from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.container import Container
from audex.service.doctor import DoctorService


@ui.page("/voiceprint/enroll")
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
) -> None:
    # Check authentication
    await doctor_service.current_doctor()

    # Header navigation
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("声纹注册").classes("text-h6")
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props(
            "flat round"
        ).tooltip("返回主面板")

    # Main content
    with ui.column().classes("w-full p-8 items-center"):
        ui.label("声纹注册").classes("text-h4 mb-4")

        with ui.card().classes("w-full max-w-2xl p-8 text-center"):
            ui.icon("fingerprint", size="4em").classes("text-warning mb-4")
            ui.label("功能开发中").classes("text-h6 mb-2")
            ui.label("声纹注册功能即将上线").classes("text-caption text-grey-7")
