from __future__ import annotations

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.config import Config
from audex.container import Container
from audex.exceptions import ValidationError
from audex.service.doctor import DoctorService
from audex.service.doctor.types import UpdateCommand
from audex.valueobj.common.auth import Password
from audex.valueobj.common.email import Email
from audex.valueobj.common.phone import CNPhone
from audex.view.decorators import handle_errors


@ui.page("/settings")
@handle_errors
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
    config: Config = Depends(Provide[Container.config]),
) -> None:
    """Render settings page."""

    # Get current doctor
    doctor = await doctor_service.current_doctor()

    # Add CSS
    ui.add_head_html('<link rel="stylesheet" href="/static/css/settings.css">')
    if config.core.app.theme == "performance":
        ui.add_head_html(
            "<script>document.documentElement.setAttribute('data-theme', 'performance');</script>"
        )

    # State
    current_tab = {"value": "profile"}
    is_editing = {"value": False}

    # Header
    with (
        ui.header().classes("header-glass items-center justify-between px-6 py-3"),
        ui.row().classes("items-center gap-3"),
    ):
        ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props(
            "flat round"
        ).tooltip("返回主面板")
        ui.label("个人设置").classes("text-h6 font-semibold text-grey-9")

    # Main container
    with (
        ui.element("div")
        .classes("w-full bg-white")
        .style("display: flex; padding: 40px 80px; gap: 40px;")
    ):
        # Left sidebar: Tabs
        with ui.column().classes("gap-2").style("width: 200px; flex-shrink: 0;"):

            def switch_tab(tab: str):
                """Switch tab."""
                current_tab["value"] = tab
                is_editing["value"] = False

                # Update tab styles using classes()
                if tab == "profile":
                    profile_tab.classes(remove="tab-button", add="tab-button-active")
                    password_tab.classes(remove="tab-button-active", add="tab-button")
                else:
                    profile_tab.classes(remove="tab-button-active", add="tab-button")
                    password_tab.classes(remove="tab-button", add="tab-button-active")

                # Show/hide content
                profile_content.visible = tab == "profile"
                password_content.visible = tab == "password"

            profile_tab = (
                ui.label("个人资料")
                .classes("tab-button-active")
                .on("click", lambda: switch_tab("profile"))
            )
            password_tab = (
                ui.label("修改密码")
                .classes("tab-button")
                .on("click", lambda: switch_tab("password"))
            )

        # Right content area (scrollable)
        content_scroll = ui.scroll_area().classes("flex-1").style("height: calc(100vh - 190px);")
        with content_scroll:
            # Profile content
            profile_content = ui.column().classes("w-full")
            with profile_content:
                # Header with edit button
                with ui.row().classes("w-full items-center justify-between mb-6"):
                    ui.label("个人资料").classes("text-h4 font-bold text-grey-9")

                    def toggle_edit():
                        """Toggle edit mode."""
                        is_editing["value"] = not is_editing["value"]

                        if is_editing["value"]:
                            edit_btn.props("icon=close")
                            edit_btn.text = "取消"
                            # Show inputs
                            info_display.visible = False
                            edit_form.visible = True
                        else:
                            edit_btn.props("icon=edit")
                            edit_btn.text = "编辑"
                            # Show info display
                            info_display.visible = True
                            edit_form.visible = False

                    edit_btn = (
                        ui.button("编辑", icon="edit", on_click=toggle_edit)
                        .props("flat no-caps")
                        .classes("action-button")
                    )

                # Info display (read-only)
                info_display = ui.column().classes("w-full gap-0")
                with info_display, ui.column().classes("w-full"):
                    with ui.element("div").classes("info-field"):
                        ui.label("姓名").classes("text-xs text-grey-6 mb-1")
                        ui.label(doctor.name).classes("text-body1 text-grey-9 font-medium")

                    with ui.element("div").classes("info-field"):
                        ui.label("工号").classes("text-xs text-grey-6 mb-1")
                        ui.label(doctor.eid).classes("text-body1 text-grey-9 font-medium")

                    with ui.row().classes("w-full gap-8"):
                        with ui.column().classes("flex-1"), ui.element("div").classes("info-field"):
                            ui.label("科室").classes("text-xs text-grey-6 mb-1")
                            ui.label(doctor.department or "未填写").classes(
                                "text-body1 text-grey-9 font-medium"
                            )

                        with ui.column().classes("flex-1"), ui.element("div").classes("info-field"):
                            ui.label("职称").classes("text-xs text-grey-6 mb-1")
                            ui.label(doctor.title or "未填写").classes(
                                "text-body1 text-grey-9 font-medium"
                            )

                    with ui.element("div").classes("info-field"):
                        ui.label("医院").classes("text-xs text-grey-6 mb-1")
                        ui.label(doctor.hospital or "未填写").classes(
                            "text-body1 text-grey-9 font-medium"
                        )

                    with ui.row().classes("w-full gap-8"):
                        with ui.column().classes("flex-1"), ui.element("div").classes("info-field"):
                            ui.label("手机号").classes("text-xs text-grey-6 mb-1")
                            ui.label(str(doctor.phone) if doctor.phone else "未填写").classes(
                                "text-body1 text-grey-9 font-medium"
                            )

                        with ui.column().classes("flex-1"), ui.element("div").classes("info-field"):
                            ui.label("邮箱").classes("text-xs text-grey-6 mb-1")
                            ui.label(str(doctor.email) if doctor.email else "未填写").classes(
                                "text-body1 text-grey-9 font-medium"
                            )

                # Edit form (hidden initially)
                edit_form = ui.column().classes("w-full gap-4")
                edit_form.visible = False
                with edit_form:
                    name_input = (
                        ui.input("", placeholder="姓名")
                        .classes("w-full clean-input")
                        .props("standout dense hide-bottom-space")
                    )
                    name_input.value = doctor.name

                    # Two columns
                    with ui.row().classes("w-full gap-4"):
                        department_input = (
                            ui.input("", placeholder="科室")
                            .classes("flex-1 clean-input")
                            .props("standout dense hide-bottom-space")
                        )
                        department_input.value = doctor.department or ""

                        title_input = (
                            ui.input("", placeholder="职称")
                            .classes("flex-1 clean-input")
                            .props("standout dense hide-bottom-space")
                        )
                        title_input.value = doctor.title or ""

                    hospital_input = (
                        ui.input("", placeholder="医院")
                        .classes("w-full clean-input")
                        .props("standout dense hide-bottom-space")
                    )
                    hospital_input.value = doctor.hospital or ""

                    with ui.row().classes("w-full gap-4"):
                        phone_input = (
                            ui.input("", placeholder="手机号")
                            .classes("flex-1 clean-input")
                            .props("standout dense hide-bottom-space")
                        )
                        phone_input.value = str(doctor.phone) if doctor.phone else ""

                        email_input = (
                            ui.input("", placeholder="邮箱")
                            .classes("flex-1 clean-input")
                            .props("standout dense hide-bottom-space")
                        )
                        email_input.value = str(doctor.email) if doctor.email else ""

                    @handle_errors
                    async def save_profile():
                        """Save profile changes."""
                        phone = None
                        if phone_input.value.strip():
                            try:
                                phone_str = phone_input.value.strip()
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

                        await doctor_service.update(
                            UpdateCommand(
                                name=name_input.value.strip() or None,
                                department=department_input.value.strip() or None,
                                title=title_input.value.strip() or None,
                                hospital=hospital_input.value.strip() or None,
                                phone=phone,
                                email=email,
                            )
                        )

                        ui.notify("个人信息已更新", type="positive", position="top")

                        # Refresh page
                        ui.navigate.to("/settings")

                    ui.button("保存更改", on_click=save_profile).props(
                        "unelevated color=primary size=lg no-caps"
                    ).classes("action-button").style("height: 48px;")

                # Delete account section
                ui.separator().classes("my-8")

                ui.label("危险操作").classes("text-h6 font-semibold text-negative mb-2")
                ui.label("删除账号后，所有数据将被永久删除且无法恢复").classes(
                    "text-sm text-grey-7 mb-4"
                )

                @handle_errors
                async def confirm_delete():
                    """Show delete confirmation dialog."""
                    with ui.dialog() as dialog, ui.card().style("width: 450px; padding: 32px;"):
                        ui.label("确认删除账号").classes("text-h5 font-semibold mb-3 text-grey-9")
                        ui.label("此操作不可撤销。请输入您的工号以确认删除。").classes(
                            "text-body2 text-grey-7 mb-4"
                        )

                        eid_confirm = (
                            ui.input("", placeholder=f"请输入工号: {doctor.eid}")
                            .classes("w-full mb-4 clean-input")
                            .props("outlined dense")
                        )

                        @handle_errors
                        async def do_delete():
                            """Delete account."""
                            if eid_confirm.value.strip() != doctor.eid:
                                ui.notify("工号不正确", type="warning", position="top")
                                return

                            await doctor_service.delete_account()
                            dialog.close()
                            ui.notify("账号已删除", type="info", position="top")
                            ui.navigate.to("/login")

                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button("取消", on_click=dialog.close).props("flat no-caps").classes(
                                "action-button"
                            )
                            ui.button("确认删除", on_click=do_delete).props(
                                "unelevated color=negative no-caps"
                            ).classes("action-button")

                    dialog.open()

                ui.button("删除账号", on_click=confirm_delete).props(
                    "outline color=negative size=lg no-caps"
                ).classes("action-button").style("height: 48px;")

            # Password content (hidden initially)
            password_content = ui.column().classes("w-full")
            password_content.visible = False
            with password_content:
                with ui.row().classes("w-full items-center justify-between mb-6"):
                    ui.label("修改密码").classes("text-h4 font-bold text-grey-9")

                ui.label("请输入当前密码和新密码").classes("text-body2 text-grey-7 mb-6")

                with (
                    ui.column()
                    .classes("gap-4")
                    .style("max-width: 100%; width: 25vw; min-width: 300px;")
                ):
                    old_password_input = (
                        ui.input(
                            "",
                            placeholder="当前密码",
                            password=True,
                            password_toggle_button=True,
                        )
                        .classes("w-full clean-input")
                        .props("standout dense hide-bottom-space")
                    )

                    new_password_input = (
                        ui.input(
                            "",
                            placeholder="新密码",
                            password=True,
                            password_toggle_button=True,
                        )
                        .classes("w-full clean-input")
                        .props("standout dense hide-bottom-space")
                    )

                    confirm_password_input = (
                        ui.input(
                            "",
                            placeholder="确认新密码",
                            password=True,
                            password_toggle_button=True,
                        )
                        .classes("w-full clean-input")
                        .props("standout dense hide-bottom-space")
                    )

                    @handle_errors
                    async def change_password():
                        """Change password."""
                        if not old_password_input.value:
                            ui.notify("请输入当前密码", type="warning", position="top")
                            return

                        if not new_password_input.value:
                            ui.notify("请输入新密码", type="warning", position="top")
                            return

                        if new_password_input.value != confirm_password_input.value:
                            ui.notify("两次密码不一致", type="warning", position="top")
                            return

                        await doctor_service.change_password(
                            old_password=Password.parse(old_password_input.value),
                            new_password=Password.parse(new_password_input.value),
                        )

                        ui.notify("密码修改成功", type="positive", position="top")

                        old_password_input.value = ""
                        new_password_input.value = ""
                        confirm_password_input.value = ""

                    ui.button("修改密码", on_click=change_password).props(
                        "unelevated color=primary size=lg no-caps"
                    ).classes("action-button").style("height: 48px;")
