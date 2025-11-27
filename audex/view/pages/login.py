from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.config import Config
from audex.container import Container
from audex.exceptions import PermissionDeniedError
from audex.service.doctor import DoctorService
from audex.service.doctor.exceptions import InvalidCredentialsError
from audex.service.doctor.types import LoginCommand
from audex.valueobj.common.auth import Password
from audex.view.decorators import handle_errors


@ui.page("/login")
@handle_errors
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
    config: Config = Depends(Provide[Container.config]),
) -> None:
    """Render login page with clean design."""

    # Check if already logged in
    try:
        await doctor_service.current_doctor()
        ui.navigate.to("/")
        return
    except PermissionDeniedError:
        pass  # Not logged in, continue

    # Add consistent CSS
    ui.add_head_html('<link rel="stylesheet" href="/static/css/login.css">')
    if config.core.app.theme == "performance":
        ui.add_head_html(
            "<script>document.documentElement.setAttribute('data-theme', 'performance');</script>"
        )

    # Full screen container
    with (
        (
            ui.element("div")
            .classes("w-full bg-white")
            .style(
                "min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px 0; overflow-y: auto;"
            )
        ),
        ui.card().classes("login-card").style("width: 420px; max-width: 90vw; padding: 32px 36px;"),
    ):
        # Logo
        ui.image("/static/images/logo.png").classes("mx-auto mb-3 login-logo")

        # Title
        ui.label("欢迎回来").classes("gradient-title text-h5 text-center w-full mb-1")
        ui.label(f"登录 {config.core.app.app_name}").classes(
            "text-sm text-grey-7 text-center w-full mb-4"
        )

        # Input fields - only bottom border
        eid_input = (
            ui.input("", placeholder="工号")
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        password_input = (
            ui.input(
                "",
                placeholder="密码",
                password=True,
                password_toggle_button=True,
            )
            .classes("w-full mb-2 clean-input")
            .props("standout dense hide-bottom-space")
        )

        @handle_errors
        async def do_login() -> None:
            """Handle login action."""
            eid = eid_input.value.strip()
            pwd = password_input.value

            if not eid or not pwd:
                ui.notify("请输入工号和密码", type="warning", position="top")
                return

            try:
                await doctor_service.login(LoginCommand(eid=eid, password=Password.parse(pwd)))
                ui.notify("登录成功", type="positive", position="top")
                ui.navigate.to("/")
            except InvalidCredentialsError as e:
                ui.notify(e.message, type="negative", position="top")

        # Enter key to login
        password_input.on("keydown.enter", do_login)

        # Login button
        ui.button("登录", on_click=do_login).props(
            "unelevated color=primary size=lg no-caps"
        ).classes("w-full login-button mt-4").style("height: 48px;")

        # Divider
        with ui.row().classes("w-full items-center gap-4 my-3"):
            ui.separator().classes("flex-1")
            ui.label("或").classes("text-xs text-grey-6")
            ui.separator().classes("flex-1")

        # Register button
        ui.button("注册新账号", on_click=lambda: ui.navigate.to("/register")).props(
            "flat size=lg no-caps"
        ).classes("w-full register-button").style("height: 48px;")
