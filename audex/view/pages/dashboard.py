from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.config import Config
from audex.container import Container
from audex.service.doctor import DoctorService


@ui.page("/")
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
    config: Config = Depends(Provide[Container.config]),
) -> None:
    # Get current doctor (service will check auth)
    try:
        doctor = await doctor_service.current_doctor()
        has_vp = await doctor_service.has_voiceprint()
    except PermissionError:
        ui.notify("请先登录", type="warning")
        ui.navigate.to("/login")
        return

    # Header navigation
    with ui.header().classes("items-center justify-between px-4"):
        ui.label(config.core.app_name).classes("text-h6")
        with ui.row().classes("items-center gap-4"):
            ui.label(f"{doctor.name} 医生").classes("text-subtitle1")

            async def do_logout() -> None:
                """Handle logout action."""
                try:
                    await doctor_service.logout()
                    ui.notify("已退出登录", type="info")
                    ui.navigate.to("/login")
                except Exception as e:
                    ui.notify(f"退出失败: {e}", type="negative")

            ui.button(icon="logout", on_click=do_logout).props("flat round").tooltip("退出登录")

    # Main content
    with ui.column().classes("w-full p-8"):
        ui.label("主面板").classes("text-h4 mb-4")

        # Doctor info card
        with ui.card().classes("w-full max-w-4xl mb-4"), ui.row().classes("items-center gap-4"):
            ui.icon("account_circle", size="3em").classes("text-primary")
            with ui.column().classes("gap-1"):
                ui.label(f"{doctor.name} ({doctor.eid})").classes("text-h6")
                info_parts = []
                if doctor.title:
                    info_parts.append(doctor.title)
                if doctor.department:
                    info_parts.append(doctor.department)
                if doctor.hospital:
                    info_parts.append(doctor.hospital)
                if info_parts:
                    ui.label(" · ".join(info_parts)).classes("text-caption text-grey-7")

        # Feature cards
        with ui.row().classes("gap-4 flex-wrap"):
            # Start new session
            with (
                ui.card()
                .classes("w-64 cursor-pointer hover:shadow-lg transition-shadow")
                .on("click", lambda: ui.navigate.to("/recording"))
            ):
                ui.icon("mic", size="3em").classes("text-primary mb-2")
                ui.label("开始新会话").classes("text-h6 mb-2")
                ui.label("创建新的门诊录音会话").classes("text-caption text-grey-7 mb-4")
                ui.button(
                    "开始录音",
                    on_click=lambda e: e.stopPropagation() or ui.navigate.to("/recording"),
                ).props("color=primary")

            # Session history
            with (
                ui.card()
                .classes("w-64 cursor-pointer hover:shadow-lg transition-shadow")
                .on("click", lambda: ui.navigate.to("/sessions"))
            ):
                ui.icon("history", size="3em").classes("text-secondary mb-2")
                ui.label("历史会话").classes("text-h6 mb-2")
                ui.label("查看和管理历史录音").classes("text-caption text-grey-7 mb-4")
                ui.button(
                    "查看",
                    on_click=lambda e: e.stopPropagation() or ui.navigate.to("/sessions"),
                ).props("outline")

            # Voiceprint management
            with ui.card().classes("w-64"):
                ui.icon("fingerprint", size="3em").classes("text-warning mb-2")
                ui.label("声纹管理").classes("text-h6 mb-2")

                if has_vp:
                    ui.label("✓ 已注册声纹").classes("text-caption text-positive mb-4")
                    ui.button(
                        "更新声纹", on_click=lambda: ui.navigate.to("/voiceprint/update")
                    ).props("outline color=warning")
                else:
                    ui.label("⚠ 未注册声纹").classes("text-caption text-warning mb-4")
                    ui.button(
                        "注册声纹", on_click=lambda: ui.navigate.to("/voiceprint/enroll")
                    ).props("color=warning")

            # Settings
            with ui.card().classes("w-64"):
                ui.icon("settings", size="3em").classes("text-info mb-2")
                ui.label("个人设置").classes("text-h6 mb-2")
                ui.label("修改个人信息和密码").classes("text-caption text-grey-7 mb-4")
                ui.button("设置", on_click=lambda: ui.navigate.to("/settings")).props("outline")
