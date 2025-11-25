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
    ui.add_head_html("""
        <style>
            /* Smooth rendering */
            * {
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }

            /* Disable scrolling */
            html, body {
                overflow: hidden !important;
                height: 100vh;
                width: 100vw;
            }

            /* Login card with subtle shadow */
            .login-card {
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

            /* Input text color - dark */
            .clean-input .q-field__native,
            .clean-input input {
                color: #1f2937 !important;
                font-size: 15px !important;
            }

            /* Placeholder color - light gray */
            .clean-input .q-field__native::placeholder,
            .clean-input input::placeholder {
                color: #9ca3af !important;
                opacity: 1 !important;
            }

            /* Bottom border - thin gray when not focused */
            .clean-input .q-field__control:before {
                border: none !important;
                border-bottom: 1px solid rgba(0, 0, 0, 0.12) !important;
                transition: border-color 0.3s ease !important;
            }

            /* Bottom border on hover - slightly darker */
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

            /* Fix password toggle button alignment */
            .clean-input .q-field__append {
                height: 48px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }

            /* Password toggle icon color */
            .clean-input .q-field__append .q-icon {
                color: #6b7280 !important;
            }

            /* Button styles with consistent typography */
            .login-button {
                border-radius: 12px !important;
                font-size: 16px !important;
                font-weight: 500 !important;
                letter-spacing: 0.02em !important;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            }

            .login-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
            }

            .login-button:active {
                transform: translateY(0);
            }

            /* Register button - matching typography */
            .register-button {
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

            .register-button:hover {
                background: rgba(240, 241, 243, 0.9) !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
                transform: translateY(-2px);
            }

            .register-button:active {
                transform: translateY(0);
            }

            /* Pure white background */
            .bg-white {
                background: #ffffff;
            }

            /* Gradient text for title */
            .gradient-title {
                background: linear-gradient(
                    135deg,
                    #667eea 0%,
                    #764ba2 100%
                );
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: 700;
            }
        </style>
    """)

    # Full screen container - no scrolling
    with (
        (
            ui.element("div")
            .classes("w-full bg-white")
            .style(
                "height: 100vh; display: flex; align-items: center; justify-content: center; overflow: hidden;"
            )
        ),
        ui.card().classes("login-card").style("width: 420px; padding: 32px 36px;"),
    ):
        # Logo
        ui.image("assets/logo.png").classes("w-16 h-16 mx-auto mb-4")

        # Title
        ui.label("欢迎回来").classes("gradient-title text-h5 text-center w-full mb-1")
        ui.label(f"登录 {config.core.app.app_name}").classes(
            "text-sm text-grey-7 text-center w-full mb-5"
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
