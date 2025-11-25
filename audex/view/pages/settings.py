from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.container import Container
from audex.service.doctor import DoctorService


@ui.page("/settings")
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
) -> None:
    # Check authentication
    try:
        await doctor_service.current_doctor()
    except PermissionError:
        ui.notify("请先登录", type="warning")
        ui.navigate.to("/login")
        return

    # Header navigation
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("个人设置").classes("text-h6")
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/dashboard")).props(
            "flat round"
        ).tooltip("返回主面板")

    # Main content
    with ui.column().classes("w-full p-8 items-center"):
        ui.label("个人设置").classes("text-h4 mb-4")

        with ui.card().classes("w-full max-w-2xl p-8 text-center"):
            ui.icon("settings", size="4em").classes("text-info mb-4")
            ui.label("功能开发中").classes("text-h6 mb-2")
            ui.label("个人设置功能即将上线").classes("text-caption text-grey-7")
