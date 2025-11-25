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
    # Check if already logged in
    try:
        await doctor_service.current_doctor()
        ui.navigate.to("/")
        return
    except PermissionDeniedError:
        pass  # Not logged in, continue to render login page

    with ui.card().classes("absolute-center w-96"):
        # Logo
        ui.image("../../../assets/assets/logo.png").classes("w-32 h-32 mx-auto mb-4")

        # Title
        ui.label(f"{config.core.app.app_name} 登录").classes("text-h4 text-center w-full mb-4")

        # Input fields
        eid_input = ui.input("工号", placeholder="请输入工号").classes("w-full")
        password_input = ui.input(
            "密码",
            placeholder="请输入密码",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")

        # Error message
        error_label = ui.label("").classes("text-negative text-sm")
        error_label.visible = False

        @handle_errors
        async def do_login() -> None:
            """Handle login action."""
            error_label.visible = False

            eid = eid_input.value.strip()
            pwd = password_input.value

            if not eid or not pwd:
                error_label.text = "请输入工号和密码"
                error_label.visible = True
                return

            try:
                await doctor_service.login(LoginCommand(eid=eid, password=Password.parse(pwd)))

                ui.notify("登录成功", type="positive")
                ui.navigate.to("/")

            except InvalidCredentialsError as e:
                error_label.text = e.message
                error_label.visible = True

        # Enter key to login
        password_input.on("keydown.enter", do_login)

        # Action buttons
        with ui.row().classes("w-full justify-between mt-4"):
            ui.button("登录", on_click=do_login).props("color=primary")
            ui.button("注册", on_click=lambda: ui.navigate.to("/register")).props("flat")
