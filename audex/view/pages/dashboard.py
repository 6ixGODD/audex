from __future__ import annotations

import random

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.config import Config
from audex.container import Container
from audex.service.doctor import DoctorService
from audex.service.session import SessionService
from audex.view.decorators import handle_errors


@ui.page("/")
@handle_errors
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
    session_service: SessionService = Depends(Provide[Container.service.session]),
    config: Config = Depends(Provide[Container.config]),
) -> None:
    """Render dashboard page with clean Apple-inspired design."""

    # Get current doctor (service will check auth)
    doctor = await doctor_service.current_doctor()
    has_vp = await doctor_service.has_voiceprint()

    # Add minimal CSS for clean design
    ui.add_head_html('<link rel="stylesheet" href="/static/css/dashboard.css">')
    if config.core.app.theme == "performance":
        ui.add_head_html(
            "<script>document.documentElement.setAttribute('data-theme', 'performance');</script>"
        )

    # Header
    with ui.header().classes("header-glass items-center justify-between px-6 py-3"):
        with ui.row().classes("items-center gap-3"):
            ui.image("/static/images/logo.png").classes("w-10 h-10")
            ui.label(config.core.app.app_name).classes("text-h6 font-semibold text-grey-9")

        with ui.row().classes("items-center gap-4"):
            with (
                ui.card()
                .classes("px-4 py-2")
                .style(
                    "border-radius: 16px; box-shadow: none; background: rgba(248, 249, 250, 0.6); backdrop-filter: blur(20px);"
                )
            ):
                ui.label(f"{doctor.name}").classes("text-sm font-medium text-grey-9")

            @handle_errors
            async def do_logout() -> None:
                await doctor_service.logout()
                ui.notify("已退出登录", type="info")
                ui.navigate.to("/login")

            ui.button(icon="logout", on_click=do_logout).props("flat round size=md").classes(
                "press-button"
            ).tooltip("退出登录")

    # Main content
    with (
        ui.element("div")
        .classes("w-full bg-white")
        .style("display: flex; padding: 60px 80px; gap: 60px; min-height: calc(100vh - 64px);")
    ):
        # Left column
        with ui.column().classes("gap-8").style("width: 360px; flex-shrink: 0;"):
            # Welcome
            with ui.column().classes("gap-2 mb-6"):
                candidate_words = ["Hi,", "Hello,", "您好,", ":)", "欢迎回来,", "很高兴见到您,"]
                ui.label(random.choice(candidate_words)).classes("text-h3 font-bold text-grey-9")
                ui.label(doctor.name).classes("text-h2 gradient-text").style("line-height: 1.2;")

                info_parts = []
                if doctor.title:
                    info_parts.append(doctor.title)
                if doctor.department:
                    info_parts.append(doctor.department)
                if doctor.hospital:
                    info_parts.append(doctor.hospital)

                if info_parts:
                    ui.label(" · ".join(info_parts)).classes("text-body2 text-grey-6 mt-3")

            # Overview - fully transparent
            overview = await session_service.stats()
            with ui.card().classes("glass-card p-5 w-full").style("margin-top: 40px;"):
                ui.label("概览").classes("text-subtitle2 font-semibold mb-4 text-grey-8")

                with ui.column().classes("gap-3 w-full"):
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label("本月会话").classes("text-xs text-grey-7")
                        ui.label(str(overview.get("sessions_count_in_this_month", 0))).classes(
                            "text-body1 font-bold text-primary"
                        )

                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label("总会话数").classes("text-xs text-grey-7")
                        ui.label(str(overview.get("total_sessions_count", 0))).classes(
                            "text-body1 font-bold text-secondary"
                        )

                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label("录音时长").classes("text-xs text-grey-7")
                        ui.label(
                            f"{(overview.get('total_duration_in_minutes', 0) / 60.0):.2f}" + "h"
                        ).classes("text-body1 font-bold text-positive")

        # Right column - vertically centered
        with ui.element("div").style(
            "flex: 1; "
            "display: grid; "
            "grid-template-columns: repeat(2, 1fr); "
            "gap: 24px; "
            "align-content: center; "
            "max-width: 850px; "
            "margin-left: auto;"
        ):
            # Card 1: Start new session
            with (
                ui.card()
                .classes("super-card cursor-pointer p-7")
                .on("click", lambda: ui.navigate.to("/recording"))
                .style("height: 220px; display: flex; flex-direction: column;")
            ):
                ui.icon("mic", size="3em").classes("text-primary rotate-icon mb-3")
                with ui.column().classes("gap-2 mb-auto"):
                    ui.label("开始新会话").classes("text-h6 font-bold text-grey-9")
                    ui.label("创建新的门诊录音会话").classes("text-sm text-grey-7")
                ui.button("开始", icon="arrow_forward").props("color=primary flat dense").classes(
                    "press-button self-end mt-3"
                )

            # Card 2: Session history
            with (
                ui.card()
                .classes("super-card cursor-pointer p-7")
                .on("click", lambda: ui.navigate.to("/sessions"))
                .style("height: 220px; display: flex; flex-direction: column;")
            ):
                ui.icon("history", size="3em").classes("text-secondary rotate-icon mb-3")
                with ui.column().classes("gap-2 mb-auto"):
                    ui.label("历史会话").classes("text-h6 font-bold text-grey-9")
                    ui.label("查看和管理历史录音").classes("text-sm text-grey-7")
                ui.button("查看", icon="arrow_forward").props("color=secondary flat dense").classes(
                    "press-button self-end mt-3"
                )

            # Card 3: Voiceprint
            with (
                ui.card()
                .classes("super-card cursor-pointer p-7")
                .on(
                    "click",
                    lambda: ui.navigate.to(
                        "/voiceprint/update" if has_vp else "/voiceprint/enroll"
                    ),
                )
                .style("height: 220px; display: flex; flex-direction: column;")
            ):
                ui.icon("fingerprint", size="3em").classes("text-warning rotate-icon mb-3")
                with ui.column().classes("gap-2 mb-auto"):
                    ui.label("声纹管理").classes("text-h6 font-bold text-grey-9")
                    if has_vp:
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("check_circle", size="sm").classes("text-positive")
                            ui.label("已注册").classes("text-sm text-positive font-medium")
                    else:
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("warning", size="sm").classes("text-warning")
                            ui.label("未注册").classes("text-sm text-warning font-medium")
                ui.button("管理" if has_vp else "注册", icon="arrow_forward").props(
                    "color=warning flat dense"
                ).classes("press-button self-end mt-3")

            # Card 4: Settings
            with (
                ui.card()
                .classes("super-card cursor-pointer p-7")
                .on("click", lambda: ui.navigate.to("/settings"))
                .style("height: 220px; display: flex; flex-direction: column;")
            ):
                ui.icon("settings", size="3em").classes("text-info rotate-icon mb-3")
                with ui.column().classes("gap-2 mb-auto"):
                    ui.label("个人设置").classes("text-h6 font-bold text-grey-9")
                    ui.label("修改个人信息和密码").classes("text-sm text-grey-7")
                ui.button("设置", icon="arrow_forward").props("color=info flat dense").classes(
                    "press-button self-end mt-3"
                )
