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
    """Render recording session page with lyrics-style scrolling."""

    doctor = await doctor_service.current_doctor()
    has_vp = await doctor_service.has_voiceprint()

    if not has_vp:
        ui.notify("请先注册声纹后再使用录音功能", type="warning", position="top")
        ui.navigate.to("/voiceprint/enroll")
        return

    ui.add_head_html('<link rel="stylesheet" href="/static/css/recording.css">')

    # Global auto-scroll JavaScript
    ui.add_head_html('<script src="/static/js/recording.js"></script>')

    # Tasks
    asyncio_tasks: dict[str, asyncio.Task] = {}

    # State variables
    session_id_state: dict[str, str | None] = {"value": session_id}
    is_recording = {"value": False}
    session_context: dict[str, t.Any] = {"value": None}
    is_session_completed = {"value": False}

    current_utterance_element: dict[str, t.Any] = {"element": None}
    current_sequence: dict[str, int] = {"value": 0}

    # Loading overlay
    loading_overlay = ui.element("div").classes("loading-overlay")
    with loading_overlay:
        ui.element("div").classes("loading-spinner-large")
    loading_overlay.visible = False

    # Header with glass effect
    with (
        ui.header().classes("header-glass items-center justify-between px-6 py-3"),
        ui.row().classes("items-center gap-3"),
    ):
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props(
            "flat round"
        ).tooltip("返回主面板")
        ui.label("录音会话").classes("text-h6 font-semibold text-grey-8")

    # Scroll to bottom button
    (
        ui.button(
            icon="keyboard_arrow_down", on_click=lambda: ui.run_javascript("scrollToBottom()")
        )
        .props("round color=white text-color=grey-8")
        .classes("scroll-bottom-btn")
        .tooltip("滚动到底部")
    )

    # Main scrollable container
    lyrics_container = ui.element("div").classes("lyrics-container").props('id="lyrics-container"')
    with lyrics_container:
        lyrics_column = ui.column().classes("w-full items-center")

    # Footer glass overlay
    ui.element("div").classes("footer-glass")

    async def load_existing_utterances():
        """Load existing conversation history."""
        if not session_id_state["value"]:
            return

        try:
            utterances = await session_service.get_utterances(session_id_state["value"])

            for utterance in utterances:
                with lyrics_column:
                    elem = ui.element("div").classes("utterance-final")

                    if utterance.speaker.value == "doctor":
                        elem.classes(add="is-doctor")
                        with elem:
                            ui.label("医生").classes("speaker-label")
                            ui.html(
                                f'<div class="bubble-doctor">{utterance.text}</div>', sanitize=False
                            )
                    else:
                        elem.classes(add="is-patient")
                        with elem:
                            ui.label("患者").classes("speaker-label")
                            ui.html(
                                f'<div class="bubble-patient">{utterance.text}</div>',
                                sanitize=False,
                            )

                current_sequence["value"] = max(current_sequence["value"], utterance.sequence)

            # JavaScript handles auto-scroll via MutationObserver

        except Exception as e:
            print(f"Failed to load utterances: {e}")

    async def wait_for_vpr_and_render(
        elem: ui.element, sequence: int, text: str, max_retries: int = 30
    ):
        """Wait for VPR completion and render final bubble."""
        ctx = session_context["value"]

        for _ in range(max_retries):
            is_doctor = ctx._vpr_results.get(sequence)

            if is_doctor is not None:
                elem.classes(remove="utterance-item utterance-current utterance-past")
                elem.classes(add="utterance-final")

                if is_doctor:
                    elem.classes(add="is-doctor")
                else:
                    elem.classes(add="is-patient")

                elem.clear()
                with elem:
                    ui.label("医生" if is_doctor else "患者").classes("speaker-label")
                    ui.html(
                        f'<div class="bubble-{"doctor" if is_doctor else "patient"}">{text}</div>',
                        sanitize=False,
                    )

                # JavaScript MutationObserver will handle auto-scroll
                return

            await asyncio.sleep(0.1)

        # Timeout - default to patient
        elem.classes(remove="utterance-item utterance-current utterance-past")
        elem.classes(add="utterance-final is-patient")
        elem.clear()
        with elem:
            ui.label("患者").classes("speaker-label")
            ui.html(f'<div class="bubble-patient">{text}</div>', sanitize=False)

    async def process_transcription():
        """Process transcription events."""
        ctx = session_context["value"]

        async for event in ctx.receive():
            if isinstance(event, Start):
                with lyrics_column:
                    elem = ui.element("div").classes("utterance-item utterance-current slide-up")
                    with elem:
                        ui.label("")
                current_utterance_element["element"] = elem

            elif isinstance(event, Delta):
                elem = current_utterance_element["element"]

                if elem is None:
                    with lyrics_column:
                        elem = ui.element("div").classes(
                            "utterance-item utterance-current slide-up"
                        )
                        with elem:
                            ui.label("")
                    current_utterance_element["element"] = elem

                elem.clear()
                with elem:
                    ui.label(event.text)

                if not event.interim and event.sequence is not None:
                    current_sequence["value"] = event.sequence
                    elem.classes(remove="utterance-current")
                    elem.classes(add="utterance-past")

                # JavaScript MutationObserver handles auto-scroll

            elif isinstance(event, Done):
                elem = current_utterance_element["element"]
                if elem and current_sequence["value"] > 0:
                    vpr_and_render_task = asyncio.create_task(
                        wait_for_vpr_and_render(elem, current_sequence["value"], event.full_text)
                    )
                    asyncio_tasks.setdefault(
                        f"vpr_render_{current_sequence['value']}", vpr_and_render_task
                    )
                    current_utterance_element["element"] = None

    @handle_errors
    async def toggle_recording():
        """Toggle recording state."""
        if not is_recording["value"]:
            if is_session_completed["value"] and session_id_state["value"]:
                # Continue existing session
                loading_overlay.visible = True
                try:
                    ctx = await session_service.session(session_id_state["value"])
                    session_context["value"] = ctx
                    await ctx.start()

                    is_recording["value"] = True
                    is_session_completed["value"] = False

                    record_btn.props("icon=stop color=negative")
                    record_btn.classes(add="recording-pulse")

                    ui.notify("继续录音", type="positive")

                    transcription_task = asyncio.create_task(process_transcription())
                    asyncio_tasks.setdefault("transcription", transcription_task)

                finally:
                    loading_overlay.visible = False

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
                        loading_overlay.visible = True

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

                            ui.notify("开始录音", type="positive")

                            transcription_task = asyncio.create_task(process_transcription())
                            asyncio_tasks.setdefault("transcription", transcription_task)

                        finally:
                            loading_overlay.visible = False

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
            loading_overlay.visible = True

            try:
                ctx = session_context["value"]
                await ctx.close()

                await session_service.complete(session_id_state["value"])

                is_recording["value"] = False
                is_session_completed["value"] = True

                record_btn.props("icon=mic color=primary")
                record_btn.classes(remove="recording-pulse")

                ui.notify("录音已保存，可继续添加内容", type="positive", timeout=3000)

            finally:
                loading_overlay.visible = False

    # Recording button
    record_btn = (
        ui.button(icon="mic", on_click=toggle_recording)
        .props("round unelevated color=primary size=xl")
        .classes("record-btn")
    )

    # Load existing utterances on page load
    await load_existing_utterances()
