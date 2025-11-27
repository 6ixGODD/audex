from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.config import Config
from audex.container import Container
from audex.service.doctor import DoctorService
from audex.service.session import SessionService
from audex.view.decorators import handle_errors


@ui.page("/sessions")
@handle_errors
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
    session_service: SessionService = Depends(Provide[Container.service.session]),
    config: Config = Depends(Provide[Container.config]),
) -> None:
    """Render sessions history page with clean design."""

    # Get current doctor
    doctor = await doctor_service.current_doctor()

    # Add CSS
    ui.add_head_html('<link rel="stylesheet" href="/static/css/sessions/styles.css">')
    if config.core.app.theme == "performance":
        ui.add_head_html(
            "<script>document.documentElement.setAttribute('data-theme', 'performance');</script>"
        )

    # Fetch sessions
    sessions = await session_service.list(doctor_id=doctor.id, page_size=100)

    # Dialog Functions
    async def show_delete_dialog(session_id: str, session_name: str):
        """Show delete confirmation dialog."""
        with (
            ui.dialog() as dialog,
            ui.card().classes("dialog-card").style("width: 450px; padding: 28px;"),
        ):
            with ui.row().classes("w-full items-center mb-6"):
                ui.icon("warning", size="xl").classes("text-warning")
                ui.label("确认删除").classes("text-h5 font-bold text-grey-9 ml-3 flex-1")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            ui.label(f"确定要删除会话「{session_name}」吗？").classes("text-body1 text-grey-8 mb-2")
            ui.label("此操作不可恢复。").classes("text-body2 text-grey-7 mb-6")

            with ui.row().classes("w-full gap-3 justify-end"):
                ui.button("取消", on_click=dialog.close).props(
                    "outline color=grey-8 no-caps"
                ).classes("action-btn btn-secondary")

                async def do_delete():
                    dialog.close()
                    try:
                        await session_service.delete(session_id)
                        ui.notify("会话已删除", type="positive", position="top")
                        ui.navigate.to("/sessions")
                    except Exception:
                        ui.notify("删除失败", type="negative", position="top")

                ui.button("删除", on_click=do_delete).props(
                    "unelevated color=negative no-caps"
                ).classes("action-btn")

        dialog.open()

    # Header
    with ui.header().classes("header-glass items-center justify-between px-6 py-4"):
        with ui.row().classes("items-center gap-3"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props("flat round")
            ui.label("历史会话").classes("text-h6 font-semibold text-grey-9")

        with ui.row().classes("items-center gap-2"):
            ui.button(
                "导出", icon="download", on_click=lambda: ui.navigate.to("/sessions/export")
            ).props("flat no-caps").classes("header-btn export-btn")

            ui.button("新建录音", on_click=lambda: ui.navigate.to("/recording")).props(
                "unelevated color=primary no-caps"
            ).classes("header-btn")

    # Main Content
    if not sessions:
        with (
            ui.element("div")
            .classes("w-full bg-white")
            .style(
                "display: flex; align-items: center; justify-content: center; "
                "min-height: calc(100vh - 64px);"
            ),
            ui.element("div").classes("empty-state"),
        ):
            ui.icon("chat_bubble_outline", size="4em").classes("text-grey-4 mb-4")
            ui.label("还没有会话记录").classes("text-h5 font-semibold text-grey-7 mb-2")
            ui.label("开始您的第一次录音会话").classes("text-body2 text-grey-6 mb-6")
            ui.button("创建新会话", on_click=lambda: ui.navigate.to("/recording")).props(
                "color=primary size=lg no-caps"
            )

    else:
        with (
            ui.scroll_area().classes("w-full").style("height: calc(100vh - 64px);"),
            (
                ui.element("div")
                .classes("w-full bg-white")
                .style(
                    "display: flex; justify-content: center; align-items: flex-start; "
                    "min-height: 100%; padding: 60px 80px;"
                )
            ),
            ui.element("div").style(
                "display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; "
                "max-width: 850px; width: 100%;"
            ),
        ):
            for session in sessions:
                with ui.card().classes("super-card cursor-pointer p-7"):
                    with ui.row().classes("items-start justify-between w-full mb-2"):
                        ui.label(session.patient_name or "未知患者").classes(
                            "text-h6 font-bold text-grey-9"
                        )

                        if session.status.value != "DRAFT":
                            status_map = {
                                "COMPLETED": ("已完成", "status-completed"),
                                "IN_PROGRESS": ("进行中", "status-in-progress"),
                                "CANCELLED": ("已取消", "status-cancelled"),
                            }
                            if session.status.value in status_map:
                                status_text, status_class = status_map[session.status.value]
                                ui.html(
                                    f'<div class="status-badge {status_class}">{status_text}</div>',
                                    sanitize=False,
                                )

                    with ui.column().classes("gap-2 mb-auto"):
                        if session.clinic_number:
                            ui.label(f"门诊号: {session.clinic_number}").classes(
                                "text-sm text-grey-7"
                            )
                        if session.medical_record_number:
                            ui.label(f"病历号: {session.medical_record_number}").classes(
                                "text-sm text-grey-7"
                            )
                        if session.diagnosis:
                            ui.label(f"诊断: {session.diagnosis}").classes("text-sm text-grey-7")

                        time_text = session.created_at.strftime("%m月%d日 %H:%M")
                        if session.started_at:
                            time_text = session.started_at.strftime("%m月%d日 %H:%M")
                        ui.label(time_text).classes("text-sm text-grey-6")

                    with ui.element("div").classes("button-layout"):

                        def create_delete_handler(sid, sname):
                            async def handler():
                                await show_delete_dialog(sid, sname)

                            return handler

                        ui.button(
                            icon="delete_outline",
                            on_click=create_delete_handler(
                                session.id, session.patient_name or "未知患者"
                            ),
                        ).props("flat").classes("btn-delete")

                        with ui.element("div").classes("right-buttons"):

                            def create_view_handler(sid):
                                def handler():
                                    ui.navigate.to(f"/sessions/details?session_id={sid}")

                                return handler

                            ui.button(
                                "查看",
                                icon="visibility",
                                on_click=create_view_handler(session.id),
                            ).props("outline color=grey-8 no-caps").classes(
                                "action-btn btn-secondary"
                            )

                            def create_continue_handler(sid):
                                def handler():
                                    ui.navigate.to(f"/recording?session_id={sid}")

                                return handler

                            ui.button(
                                "继续",
                                icon="play_arrow",
                                on_click=create_continue_handler(session.id),
                            ).props("unelevated color=primary no-caps").classes(
                                "action-btn btn-primary"
                            )
