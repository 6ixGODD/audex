from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from fastapi import Query
from nicegui import ui

from audex.config import Config
from audex.container import Container
from audex.service.session import SessionService
from audex.service.session.types import UpdateSessionCommand
from audex.view.decorators import handle_errors


@ui.page("/sessions/details")
@handle_errors
@inject
async def render(
    session_service: SessionService = Depends(Provide[Container.service.session]),
    config: Config = Depends(Provide[Container.config]),
    session_id: str = Query(...),
) -> None:
    """Render session detail page with left form and right
    conversation."""
    # Add CSS
    ui.add_head_html('<link rel="stylesheet" href="/static/css/sessions/styles.css">')
    if config.core.app.theme == "performance":
        ui.add_head_html(
            "<script>document.documentElement.setAttribute('data-theme', 'performance');</script>"
        )

    # Fetch session and utterances
    session = await session_service.get(session_id)
    if not session:
        ui.notify("会话不存在", type="negative", position="top")
        ui.navigate.to("/sessions")
        return

    utterances = await session_service.get_utterances(session_id)

    # State
    is_editing = {"value": False}

    # Header
    with ui.header().classes("header-glass items-center justify-between px-6 py-3"):
        with ui.row().classes("items-center gap-3"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/sessions")).props(
                "flat round"
            ).tooltip("返回历史会话")
            ui.label(f"{session.patient_name or '未知患者'}").classes(
                "text-h6 font-semibold text-grey-9"
            )

        ui.button(
            "继续录音",
            icon="mic",
            on_click=lambda: ui.navigate.to(f"/recording?session_id={session_id}"),
        ).props("unelevated color=primary no-caps").classes("header-btn")

    # Main container
    with (
        ui.element("div")
        .classes("w-full bg-white")
        .style("display: flex; padding: 40px 80px; gap: 40px;")
    ):
        # Left sidebar: Details
        with ui.column().classes("gap-2").style("width: 450px; flex-shrink: 0;"):
            # Header with edit button
            with ui.row().classes("w-full items-center justify-between mb-6"):
                ui.label("会话信息").classes("text-h4 font-bold text-grey-9")

                def toggle_edit():
                    """Toggle edit mode."""
                    is_editing["value"] = not is_editing["value"]

                    if is_editing["value"]:
                        edit_btn.props("icon=close")
                        edit_btn.text = "取消"
                        info_display.visible = False
                        edit_form.visible = True
                    else:
                        edit_btn.props("icon=edit")
                        edit_btn.text = "编辑"
                        info_display.visible = True
                        edit_form.visible = False

                edit_btn = (
                    ui.button("编辑", icon="edit", on_click=toggle_edit)
                    .props("flat no-caps")
                    .classes("action-button")
                )

            # Info display (read-only)
            info_display = ui.column().classes("w-full gap-0")
            with info_display:
                with ui.element("div").classes("info-field"):
                    ui.label("患者姓名").classes("text-xs text-grey-6 mb-1")
                    ui.label(session.patient_name or "未填写").classes(
                        "text-body1 text-grey-9 font-medium"
                    )

                with ui.element("div").classes("info-field"):
                    ui.label("门诊号").classes("text-xs text-grey-6 mb-1")
                    ui.label(session.clinic_number or "未填写").classes(
                        "text-body1 text-grey-9 font-medium"
                    )

                with ui.element("div").classes("info-field"):
                    ui.label("病历号").classes("text-xs text-grey-6 mb-1")
                    ui.label(session.medical_record_number or "未填写").classes(
                        "text-body1 text-grey-9 font-medium"
                    )

                with ui.element("div").classes("info-field"):
                    ui.label("诊断").classes("text-xs text-grey-6 mb-1")
                    ui.label(session.diagnosis or "未填写").classes(
                        "text-body1 text-grey-9 font-medium"
                    )

                if session.notes:
                    with ui.element("div").classes("info-field"):
                        ui.label("备注").classes("text-xs text-grey-6 mb-1")
                        ui.label(session.notes).classes("text-body1 text-grey-9 font-medium")

            # Edit form - 复用 recording 的模态框样式
            edit_form = ui.column().classes("w-full gap-4")
            edit_form.visible = False
            with edit_form:
                with ui.row().classes("w-full gap-4"):
                    patient_name_input = (
                        ui.input("", placeholder="患者姓名")
                        .classes("flex-1 clean-input")
                        .props("standout dense hide-bottom-space")
                    )
                    patient_name_input.value = session.patient_name or ""

                    clinic_number_input = (
                        ui.input("", placeholder="门诊号")
                        .classes("flex-1 clean-input")
                        .props("standout dense hide-bottom-space")
                    )
                    clinic_number_input.value = session.clinic_number or ""

                with ui.row().classes("w-full gap-4 mt-3"):
                    medical_record_number_input = (
                        ui.input("", placeholder="病历号")
                        .classes("flex-1 clean-input")
                        .props("standout dense hide-bottom-space")
                    )
                    medical_record_number_input.value = session.medical_record_number or ""

                    diagnosis_input = (
                        ui.input("", placeholder="诊断")
                        .classes("flex-1 clean-input")
                        .props("standout dense hide-bottom-space")
                    )
                    diagnosis_input.value = session.diagnosis or ""

                notes_input = (
                    ui.textarea("", placeholder="备注")
                    .classes("w-full mt-3 clean-input notes-textarea")
                    .props("standout hide-bottom-space")
                )
                notes_input.value = session.notes or ""

                @handle_errors
                async def save_session():
                    """Save session changes."""
                    await session_service.update(
                        UpdateSessionCommand(
                            session_id=session_id,
                            patient_name=patient_name_input.value.strip() or None,
                            clinic_number=clinic_number_input.value.strip() or None,
                            medical_record_number=medical_record_number_input.value.strip() or None,
                            diagnosis=diagnosis_input.value.strip() or None,
                            notes=notes_input.value.strip() or None,
                        )
                    )

                    ui.notify("会话信息已更新", type="positive", position="top")
                    ui.navigate.to(f"/sessions/details?session_id={session_id}")

                ui.button("保存更改", on_click=save_session).props(
                    "unelevated color=primary size=lg no-caps"
                ).classes("action-button").style("height: 48px;")

        # Right content area: Utterances (scrollable)
        content_scroll = (
            ui.scroll_area()
            .classes("flex-1")
            .style("height: calc(100vh - 190px); padding: 0 20px;")
        )
        with content_scroll:
            if not utterances:
                with (
                    ui.element("div")
                    .classes("empty-content")
                    .style(
                        "height: 100%; display: flex; align-items: center; justify-content: center;"
                    ),
                    ui.column().classes("items-center"),
                ):
                    ui.icon("chat_bubble_outline", size="3xl").classes("text-grey-4 mb-4")
                    ui.label("暂无对话记录").classes("text-lg text-grey-6")
            else:
                with ui.element("div").classes("utterances-container"):
                    for utterance in utterances:
                        speaker_name = "医生" if utterance.is_doctor else "患者"
                        time_str = utterance.timestamp.strftime("%H:%M:%S")
                        duration = f"{utterance.duration_ms / 1000:.1f}s"

                        if utterance.is_doctor:
                            with ui.element("div").classes("utterance-final is-doctor"):
                                ui.label(f"{speaker_name} • {time_str} • {duration}").classes(
                                    "speaker-label"
                                )
                                ui.html(
                                    f'<div class="bubble-doctor">{utterance.text}</div>',
                                    sanitize=False,
                                )
                        else:
                            with ui.element("div").classes("utterance-final is-patient"):
                                ui.label(f"{speaker_name} • {time_str} • {duration}").classes(
                                    "speaker-label"
                                )
                                ui.html(
                                    f'<div class="bubble-patient">{utterance.text}</div>',
                                    sanitize=False,
                                )
