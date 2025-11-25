from __future__ import annotations

import asyncio
import typing as t

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.container import Container
from audex.service.doctor import DoctorService
from audex.view.decorators import handle_errors


@ui.page("/voiceprint/update")
@handle_errors
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
) -> None:
    """Render voiceprint update page."""

    # Check if has voiceprint
    has_vp = await doctor_service.has_voiceprint()
    if not has_vp:
        ui.notify("您还未注册声纹，请先注册", type="warning", position="top")
        ui.navigate.to("/voiceprint/enroll")
        return

    # Add CSS
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
            }

            .header-glass {
                backdrop-filter: blur(80px) saturate(200%) !important;
                background: rgba(255, 255, 255, 0.5) !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
            }

            .bg-white {
                background: #ffffff;
            }

            /* Recording button - purple theme */
            .record-button {
                width: 180px !important;
                height: 180px !important;
                border-radius: 50% !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                box-shadow: 0 8px 32px rgba(124, 58, 237, 0.25) !important;
            }

            .record-button:hover:not(:disabled) {
                transform: scale(1.05);
                box-shadow: 0 12px 40px rgba(124, 58, 237, 0.35) !important;
            }

            .record-button:active:not(:disabled) {
                transform: scale(0.98);
            }

            .record-button:disabled {
                opacity: 0.4 !important;
            }

            /* Recording rings - soft purple glow */
            @keyframes pulse-ring {
                0% {
                    transform: scale(1);
                    opacity: 0.5;
                }
                100% {
                    transform: scale(1.4);
                    opacity: 0;
                }
            }

            .recording-ring {
                position: absolute;
                width: 180px;
                height: 180px;
                border-radius: 50%;
                background: radial-gradient(
                    circle,
                    transparent 50%,
                    rgba(124, 58, 237, 0.4) 50%,
                    transparent 52%
                );
                box-shadow: 0 0 20px rgba(124, 58, 237, 0.3);
                animation: pulse-ring 2.5s ease-out infinite;
            }

            /* Timer - sans-serif bold */
            .timer {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                font-size: 4rem;
                font-weight: 600;
                color: #1f2937;
                letter-spacing: 0.05em;
            }

            /* Loading overlay - simple smooth fade */
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0, 0, 0, 0.5);
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
                animation: fadeIn 0.2s ease-out;
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            /* Smooth spinner */
            .loading-spinner {
                width: 48px;
                height: 48px;
                border: 3px solid rgba(255, 255, 255, 0.2);
                border-top-color: white;
                border-radius: 50%;
                animation: smoothSpin 0.8s linear infinite;
            }

            @keyframes smoothSpin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    """)

    # State
    is_recording = {"value": False}
    update_context: dict[str, t.Any] = {"value": None}
    elapsed_time = {"value": 0}
    timer_task: dict[str, asyncio.Task[t.Any] | None] = {"value": None}

    # Header
    with (
        ui.header().classes("header-glass items-center justify-between px-6 py-3"),
        ui.row().classes("items-center gap-3"),
    ):
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props(
            "flat round"
        ).tooltip("返回主面板")
        ui.label("更新声纹").classes("text-h6 font-semibold text-grey-9")

    # Loading overlay
    loading_overlay = ui.element("div").classes("loading-overlay")
    with loading_overlay:
        ui.element("div").classes("loading-spinner")
    loading_overlay.visible = False

    # Main container
    with (
        ui.element("div")
        .classes("w-full bg-white")
        .style("height: calc(100vh - 64px); display: flex; padding: 60px 80px; gap: 80px;")
    ):
        # Left: Steps
        with ui.column().classes("gap-8").style("width: 320px; flex-shrink: 0;"):
            ui.label("操作流程").classes("text-h5 font-bold text-grey-9 mb-2")

            with ui.column().classes("gap-4"):
                with ui.row().classes("items-start gap-3"):
                    ui.label("1").classes(
                        "text-sm font-bold text-white w-6 h-6 flex items-center justify-center"
                    ).style("background: #7c3aed; border-radius: 50%;")
                    with ui.column().classes("gap-1"):
                        ui.label("点击按钮开始").classes("text-sm font-medium text-grey-9")
                        ui.label("启动录音功能").classes("text-xs text-grey-6")

                with ui.row().classes("items-start gap-3"):
                    ui.label("2").classes(
                        "text-sm font-bold text-white w-6 h-6 flex items-center justify-center"
                    ).style("background: #7c3aed; border-radius: 50%;")
                    with ui.column().classes("gap-1"):
                        ui.label("朗读右侧文字").classes("text-sm font-medium text-grey-9")
                        ui.label("清晰完整朗读").classes("text-xs text-grey-6")

                with ui.row().classes("items-start gap-3"):
                    ui.label("3").classes(
                        "text-sm font-bold text-white w-6 h-6 flex items-center justify-center"
                    ).style("background: #7c3aed; border-radius: 50%;")
                    with ui.column().classes("gap-1"):
                        ui.label("点击停止完成").classes("text-sm font-medium text-grey-9")
                        ui.label("时长 5-20 秒").classes("text-xs text-grey-6")

        # Center: Text (moved up more, bold)
        with ui.column().classes("flex-1 justify-center gap-4").style("margin-top: -60px;"):
            ui.label("请朗读：").classes("text-body1 text-grey-6")
            ui.label(doctor_service.config.vpr_text_content).classes(
                "text-h4 text-grey-9 font-semibold leading-relaxed"
            ).style("line-height: 1.8; max-width: 600px;")

        # Right: Button
        with (
            ui.column()
            .classes("items-center justify-center gap-8")
            .style("width: 300px; margin-top: -60px;")
        ):
            # Timer (sans-serif, bold)
            timer_label = ui.label("00:00").classes("timer")

            button_container = ui.element("div").style(
                "position: relative; display: flex; align-items: center; justify-content: center;"
            )

            with button_container:
                # Rings (soft purple glow)
                ring1 = ui.element("div").classes("recording-ring")
                ring1.visible = False
                ring2 = ui.element("div").classes("recording-ring").style("animation-delay: 0.8s;")
                ring2.visible = False
                ring3 = ui.element("div").classes("recording-ring").style("animation-delay: 1.6s;")
                ring3.visible = False

                @handle_errors
                async def toggle_recording():
                    """Toggle recording."""
                    if not is_recording["value"]:
                        # Start
                        ctx = await doctor_service.update_vp()
                        update_context["value"] = ctx
                        await ctx.start()

                        is_recording["value"] = True
                        elapsed_time["value"] = 0

                        record_btn.props("icon=stop color=negative")

                        ring1.visible = True
                        ring2.visible = True
                        ring3.visible = True

                        ui.notify("开始录音", type="info")
                        timer_task["value"] = asyncio.create_task(update_timer())

                    else:
                        # Stop
                        if elapsed_time["value"] < 5:
                            ui.notify("录音时间不足 5 秒，请继续", type="warning")
                            return

                        if timer_task["value"]:
                            timer_task["value"].cancel()

                        loading_overlay.visible = True
                        record_btn.props("icon=mic color=grey")
                        record_btn.disable()

                        ring1.visible = False
                        ring2.visible = False
                        ring3.visible = False

                        try:
                            ctx = update_context["value"]
                            result = await ctx.close()

                            is_recording["value"] = False

                            ui.notify(
                                f"声纹更新成功！录音时长: {result.duration_ms / 1000:.1f}秒",
                                type="positive",
                            )

                            await asyncio.sleep(2)
                            ui.navigate.to("/")

                        finally:
                            loading_overlay.visible = False

                async def update_timer():
                    try:
                        while is_recording["value"]:
                            await asyncio.sleep(1)
                            elapsed_time["value"] += 1

                            minutes = elapsed_time["value"] // 60
                            seconds = elapsed_time["value"] % 60
                            timer_label.text = f"{minutes:02d}:{seconds:02d}"

                            if elapsed_time["value"] >= 20:
                                await toggle_recording()
                                break
                    except asyncio.CancelledError:
                        pass

                record_btn = (
                    ui.button(icon="mic", on_click=toggle_recording)
                    .props("round unelevated color=purple size=xl")
                    .classes("record-button")
                    .style("font-size: 3em !important;")
                )

            ui.label("点击按钮开始录音").classes("text-sm text-grey-6")
