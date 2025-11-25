from __future__ import annotations

import asyncio
import typing as t

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
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
) -> None:
    """Render recording session page with lyrics-style scrolling."""

    doctor = await doctor_service.current_doctor()
    has_vp = await doctor_service.has_voiceprint()

    if not has_vp:
        ui.notify("请先注册声纹后再使用录音功能", type="warning", position="top")
        ui.navigate.to("/voiceprint/enroll")
        return

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
                background: linear-gradient(135deg, #fafbfc 0%, #f8fafc 100%);
                margin: 0 !important;
                padding: 0 !important;
            }

            /* Hide scrollbars completely */
            ::-webkit-scrollbar {
                display: none !important;
            }

            * {
                -ms-overflow-style: none !important;
                scrollbar-width: none !important;
            }

            .nicegui-content {
                padding: 0 !important;
                margin: 0 !important;
            }

            .q-page {
                padding: 0 !important;
                margin: 0 !important;
            }

            /* Header with extreme blur and early fade */
            .header-glass {
                backdrop-filter: blur(120px) saturate(400%) !important;
                -webkit-backdrop-filter: blur(120px) saturate(400%) !important;
                background: linear-gradient(to bottom,
                    rgba(255, 255, 255, 0) 0%,
                    rgba(255, 255, 255, 0.05) 20%,
                    rgba(255, 255, 255, 0.15) 50%,
                    rgba(255, 255, 255, 0.4) 80%,
                    rgba(255, 255, 255, 0.8) 100%) !important;
                border: none !important;
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                z-index: 1000 !important;
                height: 64px !important;
            }

            /* Footer with extreme blur and early fade */
            .footer-glass {
                position: fixed !important;
                bottom: 0 !important;
                left: 0 !important;
                right: 0 !important;
                height: 150px !important;
                backdrop-filter: blur(200px) saturate(400%) !important;
                -webkit-backdrop-filter: blur(200px) saturate(400%) !important;
                background: linear-gradient(to top,
                    rgba(255, 255, 255, 0.9) 0%,
                    rgba(255, 255, 255, 0.6) 20%,
                    rgba(255, 255, 255, 0.3) 40%,
                    rgba(255, 255, 255, 0.1) 60%,
                    rgba(255, 255, 255, 0.03) 80%,
                    rgba(255, 255, 255, 0) 100%) !important;
                border: none !important;
                z-index: 999 !important;
                pointer-events: none !important;
            }

            /* Scroll to bottom button */
            .scroll-bottom-btn {
                position: fixed !important;
                top: 80px !important;
                right: 20px !important;
                width: 48px !important;
                height: 48px !important;
                border-radius: 50% !important;
                z-index: 1002 !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
                transition: all 0.2s ease !important;
            }

            .scroll-bottom-btn:hover {
                transform: scale(1.1) !important;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2) !important;
                /* transparent background on hover */
                background: rgba(255, 255, 255, 0.5) !important;
                backdrop-filter: blur(10px) !important;
                -webkit-backdrop-filter: blur(10px) !important;
            }

            .record-btn {
                width: 80px !important;
                height: 80px !important;
                border-radius: 50% !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                position: fixed !important;
                bottom: 30px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                z-index: 1001 !important;
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1) !important;
                pointer-events: auto !important;
            }

            .record-btn:hover {
                transform: translateX(-50%) scale(1.05) !important;
                box-shadow: 0 12px 35px rgba(0, 0, 0, 0.15) !important;
            }

            @keyframes pulse-recording {
                0%, 100% { box-shadow: 0 8px 25px rgba(239, 68, 68, 0.3), 0 0 0 0 rgba(239, 68, 68, 0.7); }
                50% { box-shadow: 0 8px 25px rgba(239, 68, 68, 0.3), 0 0 0 20px rgba(239, 68, 68, 0); }
            }

            .recording-pulse {
                animation: pulse-recording 2s ease-out infinite;
            }

            .clean-input .q-field__control {
                background: transparent !important;
                border: none !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                height: 48px !important;
            }

            .clean-input .q-field__native,
            .clean-input input,
            .clean-input textarea {
                color: #1f2937 !important;
                font-size: 15px !important;
            }

            .clean-input .q-field__native::placeholder,
            .clean-input input::placeholder,
            .clean-input textarea::placeholder {
                color: #9ca3af !important;
                opacity: 1 !important;
            }

            .clean-input .q-field__control:before {
                border: none !important;
                border-bottom: 1px solid rgba(0, 0, 0, 0.12) !important;
                transition: border-color 0.3s ease !important;
            }

            .clean-input .q-field__control:hover:before {
                border-bottom-color: rgba(0, 0, 0, 0.2) !important;
            }

            .clean-input .q-field__control:after {
                border: none !important;
                border-bottom: 2px solid rgba(37, 99, 235, 0.8) !important;
                transform: scaleX(0);
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            }

            .clean-input.q-field--focused .q-field__control:after {
                transform: scaleX(1);
            }

            .notes-textarea .q-field__control {
                height: 100px !important;
            }

            .notes-textarea textarea {
                min-height: 70px !important;
                resize: none !important;
            }

            .action-button {
                border-radius: 12px !important;
                font-size: 16px !important;
                font-weight: 500 !important;
                letter-spacing: 0.02em !important;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
                min-width: 120px !important;
            }

            .action-button:hover {
                transform: translateY(-2px);
            }

            .action-button:active {
                transform: translateY(0);
            }

            .lyrics-container {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                padding: 80px 20px 170px 20px !important;
                overflow-y: auto !important;
                overflow-x: hidden !important;
                scroll-behavior: smooth !important;
                background: transparent !important;
                z-index: 1 !important;
            }

            .utterance-item {
                width: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 16px 0;
                transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .utterance-current {
                font-size: 1.4rem;
                font-weight: 500;
                color: #1f2937;
                text-align: center;
                line-height: 1.6;
                padding: 0 20px;
            }

            .utterance-past {
                font-size: 1.2rem;
                color: #6b7280;
                opacity: 0.6;
                text-align: center;
                line-height: 1.5;
                padding: 0 20px;
            }

            .utterance-final {
                width: 100%;
                display: flex;
                flex-direction: column;
                padding: 12px 0;
                transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .utterance-final.is-doctor {
                align-items: flex-end;
            }

            .utterance-final.is-patient {
                align-items: flex-start;
            }

            .speaker-label {
                font-size: 0.75rem;
                font-weight: 500;
                color: #9ca3af;
                margin-bottom: 6px;
                padding: 0 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .bubble-doctor {
                background: #6366f1;
                color: white;
                border-radius: 20px 20px 6px 20px;
                padding: 14px 18px;
                min-width: 120px;
                max-width: min(450px, 75vw);
                word-break: break-word;
                white-space: pre-wrap;
                box-shadow: 0 4px 20px rgba(99, 102, 241, 0.25);
                font-size: 15px;
                line-height: 1.5;
                font-weight: 400;
            }

            .bubble-patient {
                background: #ffffff;
                color: #1f2937;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 20px 20px 20px 6px;
                padding: 14px 18px;
                min-width: 120px;
                max-width: min(450px, 75vw);
                word-break: break-word;
                white-space: pre-wrap;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                font-size: 15px;
                line-height: 1.5;
                font-weight: 400;
            }

            @keyframes slideUp {
                from {
                    transform: translateY(30px);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }

            .slide-up {
                animation: slideUp 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0, 0, 0, 0.4);
                backdrop-filter: blur(8px);
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            .loading-spinner-large {
                width: 48px;
                height: 48px;
                border: 3px solid rgba(255, 255, 255, 0.2);
                border-top-color: white;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
            }
        </style>
    """)

    # Global auto-scroll JavaScript
    ui.add_head_html("""
        <script>
            let autoScrollEnabled = true;

            function forceScrollToBottom() {
                if (!autoScrollEnabled) return;

                const container = document.getElementById("lyrics-container");
                if (container) {
                    // Force scroll to bottom multiple ways
                    container.scrollTop = container.scrollHeight;
                    setTimeout(() => {
                        container.scrollTop = container.scrollHeight;
                    }, 50);
                }
            }

            // Watch for DOM changes and auto-scroll
            const observer = new MutationObserver(() => {
                if (autoScrollEnabled) {
                    forceScrollToBottom();
                }
            });

            // Start observing when page loads
            document.addEventListener('DOMContentLoaded', () => {
                const container = document.getElementById("lyrics-container");
                if (container) {
                    observer.observe(container, {
                        childList: true,
                        subtree: true,
                        attributes: true,
                        characterData: true
                    });
                }
            });

            // Manual scroll to bottom function
            function scrollToBottom() {
                const container = document.getElementById("lyrics-container");
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            }
        </script>
    """)

    # Tasks
    asyncio_tasks: dict[str, asyncio.Task] = {}

    # State variables
    session_id: dict[str, str | None] = {"value": None}
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
        if not session_id["value"]:
            return

        try:
            utterances = await session_service.get_utterances(session_id["value"])

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
            if is_session_completed["value"] and session_id["value"]:
                # Continue existing session
                loading_overlay.visible = True
                try:
                    ctx = await session_service.session(session_id["value"])
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

                            session_id["value"] = session.id
                            is_session_completed["value"] = False

                            ctx = await session_service.session(session_id["value"])
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

                await session_service.complete(session_id["value"])

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
