from __future__ import annotations

import asyncio
import typing as t

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from fastapi import Query
from nicegui import ui

from audex.container import Container
from audex.service.doctor import DoctorService
from audex.service.session import SessionService
from audex.service.session.types import CreateSessionCommand
from audex.service.session.types import Delta
from audex.service.session.types import Done
from audex.service.session.types import Start
from audex.view.decorators import handle_errors


@ui.page("/recording")
@handle_errors
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
    session_service: SessionService = Depends(Provide[Container.service.session]),
    session_id: str | None = Query(default=None),
) -> None:
    """Render recording session page with waveform visualization only."""

    doctor = await doctor_service.current_doctor()
    has_vp = await doctor_service.has_voiceprint()

    if not has_vp:
        ui.notify("请先注册声纹后再使用录音功能", type="warning", position="top")
        ui.navigate.to("/voiceprint/enroll")
        return

    # Load CSS and JS
    ui.add_head_html('<link rel="stylesheet" href="/static/css/recording.css">')
    ui.add_head_html('<link rel="stylesheet" href="/static/css/waveform.css">')
    ui.add_head_html('<script src="/static/js/waveform.js"></script>')

    # Tasks
    asyncio_tasks: dict[str, asyncio.Task] = {}

    # State variables
    session_id_state: dict[str, str | None] = {"value": session_id}
    is_recording = {"value": False}
    session_context: dict[str, t.Any] = {"value": None}
    is_session_completed = {"value": False}

    current_text_label: dict[str, t.Any] = {"label": None}

    # Header with glass effect
    with (
        ui.header().classes("header-glass items-center justify-between px-6 py-3"),
        ui.row().classes("items-center gap-3"),
    ):
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props(
            "flat round"
        ).tooltip("返回主面板")
        ui.label("录音会话").classes("text-h6 font-semibold text-grey-8")

    # Waveform Section (Vertically Centered)
    with ui.element("div").classes("waveform-section"):
        # Current text display (above waveform)
        text_display_container = ui.element("div").classes("current-text-display empty")
        with text_display_container:
            current_text_label["label"] = ui.label("等待输入...").classes("text-center")

        # Waveform canvas container (below text)
        with ui.element("div").classes("waveform-container"):
            ui.html('<canvas id="waveform-canvas"></canvas>', sanitize=False)

    # Footer glass overlay
    ui.element("div").classes("footer-glass")

    async def process_transcription():
        """Process transcription events - only update current text display."""
        ctx = session_context["value"]

        async for event in ctx.receive():
            if isinstance(event, Start):
                # Clear current text display
                if current_text_label["label"]:
                    current_text_label["label"].set_text("")
                    text_display_container.classes(remove="empty")
                    text_display_container.classes(add="has-text")

            elif isinstance(event, Delta):
                # Update current text display
                if current_text_label["label"]:
                    current_text_label["label"].set_text(event.text)

            elif isinstance(event, Done):
                # Clear the text display after completion
                if current_text_label["label"]:
                    # Wait a bit before clearing so user can see the final text
                    await asyncio.sleep(0.8)
                    current_text_label["label"].set_text("等待输入...")
                    text_display_container.classes(remove="has-text")
                    text_display_container.classes(add="empty")

    @handle_errors
    async def toggle_recording():
        """Toggle recording state."""
        if not is_recording["value"]:
            if is_session_completed["value"] and session_id_state["value"]:
                # Continue existing session
                record_btn.props("loading")
                try:
                    ctx = await session_service.session(session_id_state["value"])
                    session_context["value"] = ctx
                    await ctx.start()

                    is_recording["value"] = True
                    is_session_completed["value"] = False

                    record_btn.props("icon=stop color=negative")
                    record_btn.classes(add="recording-pulse")

                    # Start waveform
                    await ui.run_javascript("startWaveform()")

                    ui.notify("继续录音", type="positive")

                    transcription_task = asyncio.create_task(process_transcription())
                    asyncio_tasks.setdefault("transcription", transcription_task)

                finally:
                    record_btn.props(remove="loading")

            else:
                # Create new session
                with (
                    ui.dialog() as dialog,
                    ui.card().style("width: 550px; padding: 32px; border-radius: 20px;"),
                ):
                    ui.label("创建录音会话").classes("text-h5 font-bold mb-2 text-grey-9")
                    ui.label("填写患者信息以开始录音").classes("text-body2 text-grey-7 mb-6")

                    with ui.row().classes("w-full gap-4"):
                        patient_name = (
                            ui.input("", placeholder="患者姓名")
                            .classes("flex-1 clean-input")
                            .props("standout dense hide-bottom-space")
                        )

                        clinic_number = (
                            ui.input("", placeholder="门诊号")
                            .classes("flex-1 clean-input")
                            .props("standout dense hide-bottom-space")
                        )

                    with ui.row().classes("w-full gap-4 mt-3"):
                        medical_record = (
                            ui.input("", placeholder="病历号")
                            .classes("flex-1 clean-input")
                            .props("standout dense hide-bottom-space")
                        )

                        diagnosis = (
                            ui.input("", placeholder="诊断")
                            .classes("flex-1 clean-input")
                            .props("standout dense hide-bottom-space")
                        )

                    notes = (
                        ui.textarea("", placeholder="备注")
                        .classes("w-full mt-3 clean-input notes-textarea")
                        .props("standout hide-bottom-space")
                    )

                    @handle_errors
                    async def do_start():
                        dialog.close()
                        record_btn.props("loading")

                        try:
                            session = await session_service.create(
                                CreateSessionCommand(
                                    doctor_id=doctor.id,
                                    patient_name=patient_name.value.strip() or None,
                                    clinic_number=clinic_number.value.strip() or None,
                                    medical_record_number=medical_record.value.strip() or None,
                                    diagnosis=diagnosis.value.strip() or None,
                                    notes=notes.value.strip() or None,
                                )
                            )

                            session_id_state["value"] = session.id
                            is_session_completed["value"] = False

                            ctx = await session_service.session(session_id_state["value"])
                            session_context["value"] = ctx
                            await ctx.start()

                            is_recording["value"] = True

                            record_btn.props("icon=stop color=negative")
                            record_btn.classes(add="recording-pulse")

                            # Start waveform
                            await ui.run_javascript("startWaveform()")

                            ui.notify("开始录音", type="positive")

                            transcription_task = asyncio.create_task(process_transcription())
                            asyncio_tasks.setdefault("transcription", transcription_task)

                        finally:
                            record_btn.props(remove="loading")

                    with ui.row().classes("w-full justify-end gap-2 mt-6"):
                        ui.button("取消", on_click=dialog.close).props("flat no-caps").classes(
                            "action-button"
                        )
                        ui.button("开始录音", on_click=do_start).props(
                            "unelevated color=primary size=lg no-caps"
                        ).classes("action-button").style("height: 48px;")

                dialog.open()

        else:
            # Stop recording
            record_btn.props("loading")

            try:
                ctx = session_context["value"]
                await ctx.close()

                await session_service.complete(session_id_state["value"])

                is_recording["value"] = False
                is_session_completed["value"] = True

                record_btn.props("icon=mic color=primary")
                record_btn.classes(remove="recording-pulse")

                # Stop waveform
                await ui.run_javascript("stopWaveform()")

                # Clear text display
                if current_text_label["label"]:
                    current_text_label["label"].set_text("等待输入...")
                    text_display_container.classes(remove="has-text")
                    text_display_container.classes(add="empty")

                ui.notify("录音已保存，可继续添加内容", type="positive", timeout=3000)

            finally:
                record_btn.props(remove="loading")

    # Recording button
    record_btn = (
        ui.button(icon="mic", on_click=toggle_recording)
        .props("round unelevated color=primary size=xl")
        .classes("record-btn")
    )
