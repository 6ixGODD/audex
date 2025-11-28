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


@ui.page("/voiceprint/enroll")
@handle_errors
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
) -> None:
    """Render voiceprint enrollment page."""

    # Check if already has voiceprint
    has_vp = await doctor_service.has_voiceprint()
    if has_vp:
        ui.notify("您已注册声纹，如需更新请使用声纹管理功能", type="info", position="top")
        ui.navigate.to("/voiceprint/update")
        return

    # Add CSS
    ui.add_head_html('<link rel="stylesheet" href="/static/css/voiceprint/enroll.css">')

    # State
    is_recording = {"value": False}
    enrollment_context: dict[str, t.Any] = {"value": None}
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
        ui.label("声纹注册").classes("text-h6 font-semibold text-grey-9")

    # Main container
    with (
        ui.element("div").classes("voiceprint-container"),
        ui.element("div").classes("voiceprint-content"),
    ):
        # Left side: Steps
        with ui.column().classes("voiceprint-steps"):
            ui.label("操作流程").classes("text-h5 font-bold text-grey-9 mb-2")

            with ui.column().classes("gap-4"):
                with ui.row().classes("items-start gap-3"):
                    ui.label("1").classes(
                        "text-sm font-bold text-white w-6 h-6 flex items-center justify-center"
                    ).style("background: #f59e0b; border-radius: 50%;")
                    with ui.column().classes("gap-1"):
                        ui.label("点击按钮开始").classes("text-sm font-medium text-grey-9")
                        ui.label("启动录音功能").classes("text-xs text-grey-6")

                with ui.row().classes("items-start gap-3"):
                    ui.label("2").classes(
                        "text-sm font-bold text-white w-6 h-6 flex items-center justify-center"
                    ).style("background: #f59e0b; border-radius: 50%;")
                    with ui.column().classes("gap-1"):
                        ui.label("朗读右侧文字").classes("text-sm font-medium text-grey-9")
                        ui.label("清晰完整朗读").classes("text-xs text-grey-6")

                with ui.row().classes("items-start gap-3"):
                    ui.label("3").classes(
                        "text-sm font-bold text-white w-6 h-6 flex items-center justify-center"
                    ).style("background: #f59e0b; border-radius: 50%;")
                    with ui.column().classes("gap-1"):
                        ui.label("点击停止完成").classes("text-sm font-medium text-grey-9")
                        ui.label("时长 5-20 秒").classes("text-xs text-grey-6")

        # Center: Text to read
        with ui.column().classes("voiceprint-text"):
            ui.label("请朗读：").classes("text-body1 text-grey-6")
            ui.label(doctor_service.config.vpr_text_content).classes(
                "text-h4 text-grey-9 font-semibold leading-relaxed"
            ).style(
                "line-height: 1. 8; "
                "word-break: keep-all; "
                "overflow-wrap: break-word; "
                "white-space: normal;"
            )

        # Right side: Recording button
        with ui.column().classes("voiceprint-button"):
            # Timer
            timer_label = ui.label("00:00").classes("timer")

            # Button container
            button_container = ui.element("div").style(
                "position: relative; display: flex; align-items: center; justify-content: center;"
            )

            with button_container:
                # Rings
                ring1 = ui.element("div").classes("recording-ring")
                ring1.visible = False
                ring2 = ui.element("div").classes("recording-ring").style("animation-delay: 0.8s;")
                ring2.visible = False
                ring3 = ui.element("div").classes("recording-ring").style("animation-delay: 1.6s;")
                ring3.visible = False

                @handle_errors
                async def toggle_recording():
                    """Toggle recording state."""
                    if not is_recording["value"]:
                        # Start
                        ctx = await doctor_service.enroll_vp()
                        enrollment_context["value"] = ctx
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

                        record_btn.props("loading icon=mic color=grey")

                        ring1.visible = False
                        ring2.visible = False
                        ring3.visible = False

                        try:
                            ctx = enrollment_context["value"]
                            result = await ctx.close()

                            is_recording["value"] = False

                            ui.notify(
                                f"声纹注册成功！录音时长: {result.duration_ms / 1000:.1f}秒",
                                type="positive",
                            )

                            await asyncio.sleep(2)
                            ui.navigate.to("/")

                        except Exception:
                            record_btn.props(remove="loading")
                            record_btn.props("icon=mic color=warning")
                            is_recording["value"] = False
                            raise

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
                    .props("round unelevated color=warning size=xl")
                    .classes("record-button")
                    .style("font-size: 3em ! important;")
                )

            # Hint
            ui.label("点击按钮开始录音").classes("text-sm text-grey-6")
