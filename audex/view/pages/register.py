from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.container import Container
from audex.exceptions import PermissionDeniedError
from audex.exceptions import ValidationError
from audex.service.doctor import DoctorService
from audex.service.doctor.types import RegisterCommand
from audex.valueobj.common.auth import Password
from audex.valueobj.common.email import Email
from audex.valueobj.common.phone import CNPhone
from audex.view.decorators import handle_errors


@ui.page("/register")
@handle_errors
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
) -> None:
    # Check if already logged in
    try:
        await doctor_service.current_doctor()
        ui.navigate.to("/")
        return
    except PermissionDeniedError:
        pass  # Not logged in, continue to render registration page

    with ui.card().classes("absolute-center w-96 max-h-screen overflow-auto"):
        # Logo
        ui.image("../../../assets/assets/logo.png").classes("w-32 h-32 mx-auto mb-4")

        # Title
        ui.label("医生注册").classes("text-h4 text-center w-full mb-4")

        # Required fields
        eid_input = ui.input("工号", placeholder="唯一工号*").classes("w-full")
        name_input = ui.input("姓名", placeholder="真实姓名*").classes("w-full")
        password_input = ui.input(
            "密码",
            placeholder="设置密码*",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")
        password2_input = ui.input(
            "确认密码",
            placeholder="再次输入密码*",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")

        # Optional fields
        ui.separator()
        ui.label("以下信息选填").classes("text-caption text-grey-7 mt-2 mb-2")
        department_input = ui.input("科室", placeholder="如：内科").classes("w-full")
        title_input = ui.input("职称", placeholder="如：主治医师").classes("w-full")
        hospital_input = ui.input("医院", placeholder="如：XX市人民医院").classes("w-full")
        phone_input = ui.input("手机号", placeholder="11位手机号").classes("w-full")
        email_input = ui.input("邮箱", placeholder="电子邮箱").classes("w-full")

        # Error message
        error_label = ui.label("").classes("text-negative text-sm")
        error_label.visible = False

        @handle_errors
        async def do_register() -> None:
            """Handle registration action."""
            error_label.visible = False

            # Validate required fields
            if not eid_input.value.strip():
                error_label.text = "请输入工号"
                error_label.visible = True
                return

            if not name_input.value.strip():
                error_label.text = "请输入姓名"
                error_label.visible = True
                return

            if not password_input.value:
                error_label.text = "请输入密码"
                error_label.visible = True
                return

            if password_input.value != password2_input.value:
                error_label.text = "两次密码不一致"
                error_label.visible = True
                return

            # Parse optional fields
            phone = None
            if phone_input.value.strip():
                try:
                    phone = CNPhone.parse(phone_input.value.strip())
                except ValidationError:
                    error_label.text = "手机号格式不正确"
                    error_label.visible = True
                    return

            email = None
            if email_input.value.strip():
                try:
                    email = Email.parse(email_input.value.strip())
                except ValidationError:
                    error_label.text = "邮箱格式不正确"
                    error_label.visible = True
                    return

            # Call service to register
            await doctor_service.register(
                RegisterCommand(
                    eid=eid_input.value.strip(),
                    password=Password.parse(password_input.value),
                    name=name_input.value.strip(),
                    department=department_input.value.strip() or None,
                    title=title_input.value.strip() or None,
                    hospital=hospital_input.value.strip() or None,
                    phone=phone,
                    email=email,
                )
            )

            ui.notify("注册成功，自动登录", type="positive")
            ui.navigate.to("/")

        # Action buttons
        with ui.row().classes("w-full justify-between mt-4"):
            ui.button("注册", on_click=do_register).props("color=primary")
            ui.button("返回登录", on_click=lambda: ui.navigate.to("/login")).props("flat")
