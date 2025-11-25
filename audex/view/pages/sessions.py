from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

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
) -> None:
    """Render sessions history page with clean design."""

    # Get current doctor
    doctor = await doctor_service.current_doctor()

    # Add clean CSS matching dashboard EXACTLY
    ui.add_head_html("""
        <style>
            * {
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }

            html, body {
                overflow: hidden !important;
                height: 100vh;
                width: 100vw;
                background: #ffffff;
            }

            .header-glass {
                backdrop-filter: blur(80px) saturate(200%) !important;
                -webkit-backdrop-filter: blur(80px) saturate(200%) !important;
                background: rgba(255, 255, 255, 0.5) !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
            }

            /* Header button */
            .header-btn {
                border-radius: 8px !important;
                min-width: 120px !important;
                height: 40px !important;
                font-size: 14px !important;
                font-weight: 500 !important;
                transition: all 0.2s ease !important;
            }

            .header-btn:hover {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
                transform: translateY(-1px);
            }

            /* Session cards - EXACTLY like dashboard super-card */
            .super-card {
                border-radius: 28px !important;
                background: rgba(255, 255, 255, 0.9) !important;
                backdrop-filter: blur(20px) !important;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06), 0 2px 8px rgba(0, 0, 0, 0.04) !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) ! important;
                height: 220px !important;
                display: flex !important;
                flex-direction: column !important;
            }

            .super-card:hover {
                transform: translateY(-6px) scale(1.02);
                box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12), 0 6px 14px rgba(0, 0, 0, 0.08) !important;
            }

            .super-card:active {
                transform: translateY(-3px) scale(1.01);
                transition: all 0.1s cubic-bezier(0.4, 0, 0.2, 1) !important;
            }

            /* Status badges */
            .status-badge {
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 500;
                display: inline-block;
            }

            .status-completed { background: #dcfce7; color: #166534; }
            .status-in-progress { background: #fef3c7; color: #92400e; }
            .status-cancelled { background: #fee2e2; color: #991b1b; }

            /* Delete button - PERFECT CIRCLE, not ellipse */
            /* Force delete button icon to be centered */
            .btn-delete .q-btn__content {
                min-width: unset !important;
                width: 100% !important;
                padding: 0 !important;
            }

            /* Action buttons */
            .action-btn {
                transition: all 0.2s ease !important;
                border-radius: 8px !important;
                min-width: 70px !important;
                height: 32px !important;
                padding: 0 12px !important;
                font-size: 13px !important;
                font-weight: 500 !important;
            }

            .action-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
            }

            .btn-primary {
                background: #3b82f6 !important;
                color: white !important;
                border: none !important;
            }

            .btn-secondary {
                background: white !important;
                color: #374151 !important;
                border: 1px solid #d1d5db ! important;
            }

            .btn-secondary:hover {
                border-color: #9ca3af !important;
            }

            /* Button layout with MORE spacing */
            .button-layout {
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                width: 100% ! important;
                margin-top: auto !important;
                gap: 16px !important; /* Add gap for spacing */
            }

            .right-buttons {
                display: flex !important;
                gap: 12px !important; /* Increased gap between right buttons */
            }

            /* Empty state */
            .empty-state {
                background: rgba(255, 255, 255, 0.7);
                backdrop-filter: blur(10px);
                border: 2px dashed rgba(0, 0, 0, 0.1);
                border-radius: 20px;
                padding: 60px 40px;
                text-align: center;
            }

            /* Dialog styles */
            .dialog-card {
                background: white !important;
                border-radius: 16px !important;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15) !important;
            }

            .empty-content {
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                text-align: center ! important;
                width: 100% !important;
                height: 100% !important;
            }

            /* Utterance styles */
            .utterances-container {
                display: flex !important;
                flex-direction: column !important;
                width: 100% ! important;
            }

            .utterance-row {
                margin-bottom: 16px;
                width: 100%;
                display: flex !important;
            }

            .utterance-meta {
                font-size: 0.75rem;
                color: #9ca3af;
                margin-bottom: 6px;
                padding: 0 8px;
            }

            .bubble {
                padding: 12px 16px;
                border-radius: 16px;
                min-width: 200px !important;
                max-width: 50% !important;
                word-break: break-word;
                line-height: 1.4;
                white-space: pre-wrap !important;
            }

            .bubble-doctor {
                background: #3b82f6;
                color: white;
                border-radius: 16px 16px 4px 16px;
            }

            .bubble-patient {
                background: #f1f5f9;
                color: #1e293b;
                border: 1px solid #e2e8f0;
                border-radius: 16px 16px 16px 4px;
            }

            .utterance-row-doctor {
                justify-content: flex-end !important;
            }

            .utterance-doctor {
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-end !important;
            }

            .utterance-doctor .utterance-meta {
                text-align: right ! important;
            }

            .utterance-row-patient {
                justify-content: flex-start !important;
            }

            .utterance-patient {
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-start !important;
            }

            .utterance-patient .utterance-meta {
                text-align: left ! important;
            }
        </style>
    """)

    # Header
    with ui.header().classes("header-glass items-center justify-between px-6 py-4"):
        with ui.row().classes("items-center gap-3"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props("flat round")
            ui.label("历史会话").classes("text-h5 font-bold")

        ui.button("新建录音", on_click=lambda: ui.navigate.to("/recording")).props(
            "no-caps"
        ).classes("header-btn")

    # Fetch sessions
    sessions = await session_service.list(doctor_id=doctor.id, page_size=100)

    if not sessions:
        # Empty state
        with (
            (
                ui.element("div")
                .classes("w-full bg-white")
                .style(
                    "display: flex; align-items: center; justify-content: center; min-height: calc(100vh - 64px);"
                )
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

        async def show_session_dialog(session_id: str):
            """Show session details dialog."""
            session = await session_service.get(session_id)
            utterances = await session_service.get_utterances(session_id)

            with (
                ui.dialog() as dialog,
                (
                    ui.card()
                    .classes("dialog-card")
                    .style("width: 900px; max-height: 80vh; padding: 0;")
                ),
            ):
                with ui.row().classes("items-center w-full p-6 pb-4"):
                    ui.label(f"会话详情: {session.patient_name or '未知患者'}").classes(
                        "text-h5 font-bold flex-1"
                    )
                    ui.button(icon="close", on_click=dialog.close).props("flat round")

                ui.separator()

                if not utterances:
                    with (
                        ui.element("div")
                        .classes("empty-content")
                        .style("height: 400px; padding: 60px;")
                    ):
                        ui.icon("chat_bubble_outline", size="3xl").classes("text-grey-4 mb-4")
                        ui.label("暂无对话记录").classes("text-lg text-grey-6")
                else:
                    with (
                        ui.scroll_area().style("height: 500px; padding: 24px;"),
                        ui.element("div").classes("utterances-container"),
                    ):
                        for utterance in utterances:
                            speaker_name = "医生" if utterance.is_doctor else "患者"
                            time_str = utterance.timestamp.strftime("%H:%M:%S")
                            duration = f"{utterance.duration_ms / 1000:.1f}s"

                            if utterance.is_doctor:
                                with (
                                    ui.element("div").classes("utterance-row utterance-row-doctor"),
                                    ui.element("div").classes("utterance-doctor"),
                                ):
                                    ui.label(f"{speaker_name} • {time_str} • {duration}").classes(
                                        "utterance-meta"
                                    )
                                    ui.html(
                                        f'<div class="bubble bubble-doctor">{utterance.text}</div>',
                                        sanitize=False,
                                    )
                            else:
                                with (
                                    ui.element("div").classes(
                                        "utterance-row utterance-row-patient"
                                    ),
                                    ui.element("div").classes("utterance-patient"),
                                ):
                                    ui.label(f"{speaker_name} • {time_str} • {duration}").classes(
                                        "utterance-meta"
                                    )
                                    ui.html(
                                        f'<div class="bubble bubble-patient">{utterance.text}</div>',
                                        sanitize=False,
                                    )

                ui.separator()

                with ui.row().classes("w-full gap-3 p-6 justify-end"):
                    ui.button("关闭", on_click=dialog.close).props(
                        "outline color=grey-8 no-caps"
                    ).classes("action-btn btn-secondary")

                    async def continue_from_dialog():
                        dialog.close()
                        ui.navigate.to(f"/recording?session_id={session_id}")

                    ui.button("继续录音", icon="mic", on_click=continue_from_dialog).props(
                        "unelevated color=primary no-caps"
                    ).classes("action-btn btn-primary")

            dialog.open()

        # Main content with SCROLL support and CENTERED layout
        with (
            ui.scroll_area().classes("w-full").style("height: calc(100vh - 64px);"),
            (
                ui.element("div")
                .classes("w-full bg-white")
                .style(
                    "display: flex; "
                    "justify-content: center; "  # Center the grid
                    "align-items: flex-start; "
                    "min-height: 100%; "
                    "padding: 60px 80px;"
                )
            ),
            ui.element("div").style(
                "display: grid; "
                "grid-template-columns: repeat(2, 1fr); "
                "gap: 24px; "
                "max-width: 850px; "
                "width: 100%; "  # Take full width up to max-width
            ),
        ):
            for session in sessions:
                with ui.card().classes("super-card cursor-pointer p-7"):
                    # Header row with status
                    with ui.row().classes("items-start justify-between w-full mb-2"):
                        ui.label(session.patient_name or "未知患者").classes(
                            "text-h6 font-bold text-grey-9"
                        )

                        # Status badge - ONLY if not draft
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

                    # Info section
                    with ui.column().classes("gap-2 mb-auto"):
                        # Show only existing info
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

                        # Time info
                        time_text = session.created_at.strftime("%m月%d日 %H:%M")
                        if session.started_at:
                            time_text = session.started_at.strftime("%m月%d日 %H:%M")
                        ui.label(time_text).classes("text-sm text-grey-6")

                    # Button layout - DELETE LEFT, BUTTONS RIGHT with MORE spacing
                    with ui.element("div").classes("button-layout"):
                        # Left: Delete button - PERFECT CIRCLE
                        def create_delete_handler(session_id, session_name):
                            async def delete_handler():
                                await show_delete_dialog(session_id, session_name)

                            return delete_handler

                        ui.button(
                            icon="delete_outline",
                            on_click=create_delete_handler(
                                session.id, session.patient_name or "未知患者"
                            ),
                        ).props("flat round").classes("btn-delete")

                        # Right: View + Continue buttons with MORE spacing
                        with ui.element("div").classes("right-buttons"):
                            # View button
                            def create_view_handler(session_id):
                                async def view_handler():
                                    await show_session_dialog(session_id)

                                return view_handler

                            ui.button(
                                "查看",
                                icon="visibility",
                                on_click=create_view_handler(session.id),
                            ).props("outline color=grey-8 no-caps").classes(
                                "action-btn btn-secondary"
                            )

                            # Continue button
                            def create_continue_handler(session_id):
                                async def continue_handler():
                                    ui.navigate.to(f"/recording? session_id={session_id}")

                                return continue_handler

                            ui.button(
                                "继续",
                                icon="play_arrow",
                                on_click=create_continue_handler(session.id),
                            ).props("unelevated color=primary no-caps").classes(
                                "action-btn btn-primary"
                            )

    async def show_delete_dialog(session_id: str, session_name: str):
        """Show delete confirmation dialog."""
        with ui.dialog() as dialog:
            with ui.card().classes("dialog-card").style("width: 450px; padding: 28px;"):
                with ui.row().classes("w-full items-center mb-6"):
                    ui.icon("warning", size="xl").classes("text-warning")
                    ui.label("确认删除").classes("text-h5 font-bold text-grey-9 ml-3 flex-1")
                    ui.button(icon="close", on_click=dialog.close).props("flat round dense")

                ui.label(f"确定要删除会话「{session_name}」吗？").classes(
                    "text-body1 text-grey-8 mb-2"
                )
                ui.label("此操作不可恢复。").classes("text-body2 text-grey-7 mb-6")

                with ui.row().classes("w-full gap-3 justify-end"):
                    ui.button("取消", on_click=dialog.close).props(
                        "outline color=grey-8 no-caps"
                    ).classes("action-btn btn-secondary")

                    async def do_delete():
                        dialog.close()
                        try:
                            await session_service.delete(session_id)
                            ui.notify("会话已删除", type="positive")
                            ui.navigate.to("/sessions")
                        except Exception:
                            ui.notify("删除失败", type="negative")

                        ui.button("删除", on_click=do_delete).props(
                            "unelevated color=negative no-caps"
                        ).classes("action-btn")

            dialog.open()
