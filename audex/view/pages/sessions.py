from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.container import Container
from audex.service.doctor import DoctorService
from audex.service.session import SessionService


@ui.page("/sessions")
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
    session_service: SessionService = Depends(Provide[Container.service.session]),
) -> None:
    # Get current doctor (service will check auth)
    try:
        doctor = await doctor_service.current_doctor()
    except PermissionError:
        ui.notify("请先登录", type="warning")
        ui.navigate.to("/login")
        return

    # Header navigation
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("历史会话").classes("text-h6")
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/dashboard")).props(
            "flat round"
        ).tooltip("返回主面板")

    # Main content
    with ui.column().classes("w-full p-8"):
        ui.label("历史会话记录").classes("text-h4 mb-4")

        # Fetch session list
        try:
            sessions = await session_service.list(
                doctor_id=doctor.id,
                page_index=0,
                page_size=50,
            )

            if not sessions:
                # Empty state
                with ui.card().classes("w-full p-8 text-center"):
                    ui.icon("folder_open", size="4em").classes("text-grey-5 mb-4")
                    ui.label("暂无会话记录").classes("text-h6 text-grey-7")
                    ui.label("创建新会话开始使用").classes("text-caption text-grey-6 mt-2")
                    ui.button(
                        "创建会话", icon="add", on_click=lambda: ui.navigate.to("/recording")
                    ).props("color=primary").classes("mt-4")
            else:
                # Sessions table
                columns = [
                    {
                        "name": "patient",
                        "label": "患者",
                        "field": "patient_name",
                        "align": "left",
                    },
                    {
                        "name": "clinic",
                        "label": "门诊号",
                        "field": "clinic_number",
                        "align": "left",
                    },
                    {"name": "status", "label": "状态", "field": "status", "align": "center"},
                    {
                        "name": "started",
                        "label": "开始时间",
                        "field": "started_at",
                        "align": "left",
                    },
                    {"name": "actions", "label": "操作", "field": "actions", "align": "center"},
                ]

                rows = [
                    {
                        "id": s.id,
                        "patient_name": s.patient_name or "-",
                        "clinic_number": s.clinic_number or "-",
                        "status": s.status.value,
                        "started_at": s.started_at.strftime("%Y-%m-%d %H:%M")
                        if s.started_at
                        else "-",
                    }
                    for s in sessions
                ]

                ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

        except PermissionError:
            ui.notify("请先登录", type="warning")
            ui.navigate.to("/login")
        except Exception as e:
            ui.notify(f"加载会话失败: {e}", type="negative")
