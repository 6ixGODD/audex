from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.config import Config
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
    config: Config = Depends(Provide[Container.config]),
) -> None:
    """Render registration page with clean design."""

    # Check if already logged in
    try:
        await doctor_service.current_doctor()
        ui.navigate.to("/")
        return
    except PermissionDeniedError:
        pass  # Not logged in, continue

    # Add consistent CSS (same as login)
    ui.add_head_html("""
        <style>
            /* Smooth rendering */
            * {
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }

            /* Allow scrolling for register page */
            html, body {
                overflow-y: auto !important;
                height: 100%;
                width: 100vw;
            }

            /* Register card */
            .register-card {
                border-radius: 28px !important;
                background: rgba(255, 255, 255, 0.95) !important;
                backdrop-filter: blur(20px) !important;
                box-shadow:
                    0 8px 32px rgba(0, 0, 0, 0.08),
                    0 4px 16px rgba(0, 0, 0, 0.05) !important;
            }

            /* Clean input - ONLY bottom border */
            .clean-input .q-field__control {
                background: transparent !important;
                border: none !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                height: 48px !important;
            }

            /* Input text color */
            .clean-input .q-field__native,
            .clean-input input {
                color: #1f2937 !important;
                font-size: 15px !important;
            }

            /* Placeholder color */
            .clean-input .q-field__native::placeholder,
            .clean-input input::placeholder {
                color: #9ca3af !important;
                opacity: 1 !important;
            }

            /* Bottom border - thin gray */
            .clean-input .q-field__control:before {
                border: none !important;
                border-bottom: 1px solid rgba(0, 0, 0, 0.12) !important;
                transition: border-color 0.3s ease !important;
            }

            .clean-input .q-field__control:hover:before {
                border-bottom-color: rgba(0, 0, 0, 0.2) !important;
            }

            /* Bottom border when focused - thick blue */
            .clean-input .q-field__control:after {
                border: none !important;
                border-bottom: 2px solid rgba(37, 99, 235, 0.8) !important;
                transform: scaleX(0);
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            }

            .clean-input.q-field--focused .q-field__control:after {
                transform: scaleX(1);
            }

            /* Fix password toggle button */
            .clean-input .q-field__append {
                height: 48px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }

            .clean-input .q-field__append .q-icon {
                color: #6b7280 !important;
            }

            /* Button styles */
            .register-button {
                border-radius: 12px !important;
                font-size: 16px !important;
                font-weight: 500 !important;
                letter-spacing: 0.02em !important;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            }

            .register-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
            }

            .register-button:active {
                transform: translateY(0);
            }

            /* Back button */
            .back-button {
                border-radius: 12px !important;
                border: none !important;
                font-size: 16px !important;
                font-weight: 500 !important;
                letter-spacing: 0.02em !important;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06) !important;
                background: rgba(248, 249, 250, 0.8) !important;
                color: #6b7280 !important;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            }

            .back-button:hover {
                background: rgba(240, 241, 243, 0.9) !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
                transform: translateY(-2px);
            }

            .back-button:active {
                transform: translateY(0);
            }

            /* Pure white background */
            .bg-white {
                background: #ffffff;
            }

            /* Gradient text */
            .gradient-title {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: 700;
            }
        </style>
    """)

    # Full screen container - allow scrolling
    with (
        (
            ui.element("div")
            .classes("w-full bg-white")
            .style(
                "min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 40px 20px;"
            )
        ),
        ui.card().classes("register-card").style("width: 480px; padding: 32px 36px;"),
    ):  # Register card
        # Logo
        ui.image("assets/logo.png").classes("w-16 h-16 mx-auto mb-3")

        # Title
        ui.label("创建账号").classes("gradient-title text-h5 text-center w-full mb-1")
        ui.label(f"注册 {config.core.app.app_name} 医生账号").classes(
            "text-sm text-grey-7 text-center w-full mb-5"
        )

        # Required fields section
        ui.label("基本信息").classes("text-subtitle2 font-semibold text-grey-8 mb-3")

        eid_input = (
            ui.input("", placeholder="工号 *")
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        name_input = (
            ui.input("", placeholder="姓名 *")
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        password_input = (
            ui.input(
                "",
                placeholder="密码 *",
                password=True,
                password_toggle_button=True,
            )
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        password2_input = (
            ui.input(
                "",
                placeholder="确认密码 *",
                password=True,
                password_toggle_button=True,
            )
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        # Optional fields section
        ui.separator().classes("my-4")
        ui.label("其他信息（选填）").classes("text-subtitle2 font-semibold text-grey-8 mb-3")

        department_input = (
            ui.input("", placeholder="科室")
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        title_input = (
            ui.input("", placeholder="职称")
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        hospital_input = (
            ui.input("", placeholder="医院")
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        phone_input = (
            ui.input("", placeholder="手机号")
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        email_input = (
            ui.input("", placeholder="邮箱")
            .classes("w-full mb-3 clean-input")
            .props("standout dense hide-bottom-space")
        )

        @handle_errors
        async def do_register() -> None:
            """Handle registration action."""
            # Validate required fields
            if not eid_input.value.strip():
                ui.notify("请输入工号", type="warning", position="top")
                return

            if not name_input.value.strip():
                ui.notify("请输入姓名", type="warning", position="top")
                return

            if not password_input.value:
                ui.notify("请输入密码", type="warning", position="top")
                return

            if password_input.value != password2_input.value:
                ui.notify("两次密码不一致", type="warning", position="top")
                return

            # Parse optional fields
            phone = None
            if phone_input.value.strip():
                try:
                    phone_str: str = phone_input.value.strip()
                    if not phone_str.startswith("+86 "):
                        phone_str = "+86 " + phone_str
                    phone = CNPhone.parse(phone_str)
                except ValidationError:
                    ui.notify("手机号格式不正确", type="warning", position="top")
                    return

            email = None
            if email_input.value.strip():
                try:
                    email = Email.parse(email_input.value.strip())
                except ValidationError:
                    ui.notify("邮箱格式不正确", type="warning", position="top")
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

            ui.notify("注册成功", type="positive", position="top")
            ui.navigate.to("/")

        # Register button
        ui.button("注册", on_click=do_register).props(
            "unelevated color=primary size=lg no-caps"
        ).classes("w-full register-button mt-4").style("height: 48px;")

        # Divider
        with ui.row().classes("w-full items-center gap-4 my-3"):
            ui.separator().classes("flex-1")
            ui.label("或").classes("text-xs text-grey-6")
            ui.separator().classes("flex-1")

        # Back to login button
        ui.button("返回登录", on_click=lambda: ui.navigate.to("/login")).props(
            "flat size=lg no-caps"
        ).classes("w-full back-button").style("height: 48px;")
