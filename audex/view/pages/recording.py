from __future__ import annotations

import asyncio

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.container import Container
from audex.service.doctor import DoctorService
from audex.service.session import SessionService
from audex.service.session.types import CreateSessionCommand


@ui.page("/recording")
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
        ui.label("录音会话").classes("text-h6")
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/dashboard")).props(
            "flat round"
        ).tooltip("返回主面板")

    # Main content
    with ui.column().classes("w-full p-8 items-center"):
        ui.label("新建录音会话").classes("text-h4 mb-4")

        # Session info form
        with ui.card().classes("w-full max-w-2xl mb-4"):
            ui.label("会话信息").classes("text-h6 mb-4")

            patient_name = ui.input("患者姓名", placeholder="选填").classes("w-full")
            clinic_number = ui.input("门诊号", placeholder="选填").classes("w-full")
            medical_record = ui.input("病历号", placeholder="选填").classes("w-full")
            diagnosis = ui.input("诊断", placeholder="选填").classes("w-full")
            notes = ui.textarea("备注", placeholder="选填").classes("w-full")

        # Recording controls
        with ui.card().classes("w-full max-w-2xl"):
            ui.label("录音控制").classes("text-h6 mb-4")

            status_label = ui.label("状态：未开始").classes("text-lg mb-4")

            # State variables
            is_recording = {"value": False}
            session_id: dict[str, str | None] = {"value": None}

            async def start_recording() -> None:
                """Handle start recording action."""
                if is_recording["value"]:
                    return

                try:
                    # Create session
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
                    is_recording["value"] = True

                    status_label.text = "状态：录音中..."
                    status_label.classes("text-positive", remove="text-negative")
                    start_btn.disable()
                    stop_btn.enable()

                    # Disable form inputs
                    patient_name.disable()
                    clinic_number.disable()
                    medical_record.disable()
                    diagnosis.disable()
                    notes.disable()

                    ui.notify("开始录音", type="positive")

                except PermissionError:
                    ui.notify("请先登录", type="warning")
                    ui.navigate.to("/login")
                except Exception as e:
                    ui.notify(f"启动录音失败: {e}", type="negative")

            async def stop_recording() -> None:
                """Handle stop recording action."""
                if not is_recording["value"]:
                    return

                try:
                    # Complete session
                    await session_service.complete(session_id["value"])

                    is_recording["value"] = False
                    status_label.text = "状态：已完成"
                    status_label.classes("text-info", remove="text-positive")
                    start_btn.enable()
                    stop_btn.disable()

                    ui.notify("录音已保存", type="positive")

                    # Navigate back after 3 seconds
                    await asyncio.sleep(3)
                    ui.navigate.to("/dashboard")

                except PermissionError:
                    ui.notify("请先登录", type="warning")
                    ui.navigate.to("/login")
                except Exception as e:
                    ui.notify(f"停止录音失败: {e}", type="negative")

            # Control buttons
            with ui.row().classes("gap-4 mb-4"):
                start_btn = ui.button("开始录音", icon="mic", on_click=start_recording).props(
                    "color=primary size=lg"
                )
                stop_btn = ui.button("停止录音", icon="stop", on_click=stop_recording).props(
                    "color=negative size=lg"
                )
                stop_btn.disable()

            # Real-time transcript display
            with ui.card().classes("w-full p-4 min-h-64 bg-grey-1"):
                ui.label("实时转写").classes("text-subtitle1 mb-2")
                ui.separator()
                transcript_area = ui.scroll_area().classes("w-full h-48 p-2")
                with transcript_area:
                    ui.label("转写内容将在这里实时显示...").classes("text-grey-6")
