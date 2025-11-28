from __future__ import annotations

import random

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi import Depends
from nicegui import ui

from audex.container import Container
from audex.service.doctor import DoctorService
from audex.service.export import ExportService
from audex.service.session import SessionService
from audex.view.decorators import handle_errors


@ui.page("/sessions/export")
@handle_errors
@inject
async def render(
    doctor_service: DoctorService = Depends(Provide[Container.service.doctor]),
    session_service: SessionService = Depends(Provide[Container.service.session]),
    export_service: ExportService = Depends(Provide[Container.service.export]),
) -> None:
    """Render export options page."""

    # Get current doctor
    doctor = await doctor_service.current_doctor()

    # Add CSS
    ui.add_head_html('<link rel="stylesheet" href="/static/css/sessions/styles.css">')

    # Fetch sessions
    sessions = await session_service.list(doctor_id=doctor.id, page_size=100)

    # State
    server_running = {"value": False}

    # Before unload script
    ui.add_head_html("""
    <script>
        window.addEventListener('beforeunload', function(e) {
            if (window.serverRunning) {
                e.preventDefault();
                e.returnValue = '服务器正在运行，确定要离开吗？';
                return e.returnValue;
            }
        });
    </script>
    """)

    # Header
    with (
        ui.header().classes("header-glass items-center justify-between px-6 py-3"),
        ui.row().classes("items-center gap-3"),
    ):

        async def go_back():
            """返回并检查服务器状态."""
            if server_running["value"]:
                with (
                    ui.dialog() as leave_dialog,
                    ui.card()
                    .classes("dialog-card")
                    .style("width: 450px; padding: 28px; border-radius: 16px;"),
                ):
                    with ui.row().classes("w-full items-center mb-6"):
                        ui.icon("warning", size="xl").classes("text-warning")
                        ui.label("确认离开").classes("text-h5 font-bold text-grey-9 ml-3 flex-1")
                        ui.button(icon="close", on_click=leave_dialog.close).props(
                            "flat round dense"
                        )

                    ui.label("服务器正在运行，离开将自动关闭服务器").classes(
                        "text-body1 text-grey-8 mb-2"
                    )
                    ui.label("确定要离开吗？").classes("text-body2 text-grey-7 mb-6")

                    with ui.row().classes("w-full gap-3 justify-end"):
                        ui.button("取消", on_click=leave_dialog.close).props(
                            "outline color=grey-8 no-caps"
                        ).classes("action-button")

                        async def confirm_leave():
                            await export_service.stop_server()
                            server_running["value"] = False
                            await ui.run_javascript("window.serverRunning = false;")
                            leave_dialog.close()
                            ui.navigate.to("/sessions")

                        ui.button("确认离开", on_click=confirm_leave).props(
                            "unelevated color=negative no-caps"
                        ).classes("action-button")

                leave_dialog.open()
            else:
                ui.navigate.to("/sessions")

        ui.button(icon="arrow_back", on_click=go_back).props("flat round").tooltip("返回历史会话")
        ui.label("导出会话").classes("text-h6 font-semibold text-grey-9")

    # Main content - 完全垂直居中于整个视口
    with (
        ui.element("div")
        .classes("w-full bg-white")
        .style(
            "position: fixed; "
            "top: 0; "
            "left: 0; "
            "right: 0; "
            "bottom: 0; "
            "display: flex; "
            "align-items: center; "
            "justify-content: center; "
            "padding: 60px 80px; "
            "padding-top: calc(108px + 30px); "
            "box-sizing: border-box; "
            "overflow: auto;"
        ),
        ui.element("div").style(
            "display: flex; gap: 60px; align-items: center; max-width: 100%; width: 100%;"
        ),
    ):
        # Left column
        with ui.column().classes("gap-8").style("width: 360px; flex-shrink: 0;"):
            # Title
            with ui.column().classes("gap-2 mb-6"):
                candidate_words = [":)", ":D", "🚀", "🎉", "😄", "👍"]
                ui.label(random.choice(candidate_words)).classes("text-h3 font-bold text-grey-9")
                ui.label("选择导出方式").classes("text-h2 gradient-text").style("line-height: 1.2;")

            # Stats
            with ui.card().classes("glass-card p-5 w-full").style("margin-top: 40px;"):
                ui.label("统计").classes("text-subtitle2 font-semibold mb-4 text-grey-8")

                with ui.column().classes("gap-3 w-full"):
                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label("会话总数").classes("text-xs text-grey-7")
                        ui.label(str(len(sessions))).classes("text-body1 font-bold text-primary")

                    with ui.row().classes("items-center justify-between w-full"):
                        ui.label("服务器状态").classes("text-xs text-grey-7")
                        status_label = ui.label("未启动").classes(
                            "text-body1 font-bold text-grey-6"
                        )

        # Right column - 2x2 grid
        with ui.element("div").style(
            "flex: 1; "
            "display: grid; "
            "grid-template-columns: repeat(2, 1fr); "
            "gap: 20px; "
            "max-width: 850px; "
            "margin-left: auto;"
        ):
            # Card 1: Server export
            server_card = (
                ui.card()
                .classes("super-card cursor-pointer")
                .style(
                    "height: 220px; "
                    "display: flex; "
                    "flex-direction: column; "
                    "padding: 1.5rem; "
                    "box-sizing: border-box;"
                )
            )

            with server_card:
                server_icon = (
                    ui.icon("cloud", size="3em")
                    .classes("text-primary rotate-icon")
                    .style("flex-shrink: 0; margin-bottom: 0.75rem;")
                )
                with ui.column().classes("gap-2").style("flex: 1;"):
                    ui.label("服务器导出").classes("text-h6 font-bold text-grey-9")
                    ui.label("通过浏览器访问导出页面").classes("text-sm text-grey-7")
                server_btn = (
                    ui.button("启动", icon="arrow_forward")
                    .props("color=primary flat dense")
                    .classes("press-button")
                    .style(
                        "align-self: flex-end; "
                        "flex-shrink: 0; "
                        "background: transparent ! important; "
                        "box-shadow: none !important;"
                    )
                )

            async def start_server_export():
                """Start or stop server export."""
                if server_running["value"]:
                    with (
                        ui.dialog() as stop_dialog,
                        ui.card()
                        .classes("dialog-card")
                        .style("width: 450px; padding: 28px; border-radius: 16px;"),
                    ):
                        with ui.row().classes("w-full items-center mb-6"):
                            ui.icon("warning", size="xl").classes("text-warning")
                            ui.label("确认关闭").classes(
                                "text-h5 font-bold text-grey-9 ml-3 flex-1"
                            )
                            ui.button(icon="close", on_click=stop_dialog.close).props(
                                "flat round dense"
                            )

                        ui.label("确定要停止服务器吗？").classes("text-body1 text-grey-8 mb-2")
                        ui.label("其他设备将无法继续访问").classes("text-body2 text-grey-7 mb-6")

                        with ui.row().classes("w-full gap-3 justify-end"):
                            ui.button("取消", on_click=stop_dialog.close).props(
                                "outline color=grey-8 no-caps"
                            ).classes("action-button")

                            async def confirm_stop():
                                await export_service.stop_server()
                                server_running["value"] = False
                                await ui.run_javascript("window.serverRunning = false;")
                                status_label.text = "未启动"
                                status_label.classes(remove="text-positive", add="text-grey-6")

                                # reset card UI
                                server_card.classes(remove="super-card-active")
                                server_icon.classes(remove="text-negative", add="text-primary")
                                server_btn.set_text("启动")
                                server_btn.props("icon=arrow_forward color=primary")

                                stop_dialog.close()
                                ui.notify("服务器已停止", type="info", position="top")

                            ui.button("确认停止", on_click=confirm_stop).props(
                                "unelevated color=negative no-caps"
                            ).classes("action-button")

                    stop_dialog.open()
                    return

                # Start server
                try:
                    info = await export_service.start_server()
                    server_running["value"] = True
                    await ui.run_javascript("window.serverRunning = true;")
                    status_label.text = "运行中"
                    status_label.classes(remove="text-grey-6", add="text-positive")

                    server_card.classes(add="super-card-active")
                    server_icon.classes(remove="text-primary", add="text-negative")
                    server_btn.set_text("停止")
                    server_btn.props("icon=stop color=negative")

                    # Show success dialog
                    with (
                        ui.dialog() as success_dialog,
                        ui.card()
                        .classes("dialog-card")
                        .style("width: 550px; padding: 32px; border-radius: 16px;"),
                    ):
                        with ui.row().classes("w-full items-center mb-6"):
                            ui.icon("check_circle", size="xl").classes("text-positive")
                            ui.label("服务器已启动").classes(
                                "text-h5 font-bold text-grey-9 q-ml-sm"
                            )
                            ui.space()
                            ui.button(icon="close", on_click=success_dialog.close).props(
                                "flat round dense"
                            )

                        # Server info
                        with ui.element("div").classes("info-box"):
                            ui.label("访问地址").classes("text-xs text-grey-6 mb-2")

                            with ui.row().classes("items-center gap-2 mb-3"):
                                ui.label(info.url).classes("text-body1 font-mono text-primary")

                                async def copy_url():
                                    await ui.run_javascript(
                                        f"navigator.clipboard.writeText('{info.url}')"
                                    )
                                    ui.notify("已复制", type="positive", position="top")

                                ui.button(icon="content_copy", on_click=copy_url).props(
                                    "flat dense round size=sm"
                                )

                            ui.element("div").classes("divider")

                            ui.label(f"主机: {info.host}").classes("text-sm text-grey-7 mb-1")
                            ui.label(f"端口: {info.port}").classes("text-sm text-grey-7")

                        ui.label("在其他设备的浏览器中打开上述地址即可访问").classes(
                            "text-body2 text-grey-6 mt-4 mb-6"
                        )

                        ui.button("知道了", on_click=success_dialog.close).props(
                            "unelevated color=primary no-caps"
                        ).classes("action-button w-full").style("height: 48px;")

                    success_dialog.open()

                except Exception:
                    ui.notify("启动失败", type="negative", position="top")

            server_card.on("click", start_server_export)

            # Card 2: USB export
            async def start_usb_export():
                """Start USB export."""
                devices = await export_service.list_usb_devices()

                if not devices:
                    with (
                        ui.dialog() as no_device_dialog,
                        ui.card()
                        .classes("dialog-card")
                        .style("width: 500px; padding: 32px; border-radius: 16px;"),
                    ):
                        with ui.row().classes("w-full items-center mb-6"):
                            ui.icon("usb_off", size="xl").classes("text-grey-4")
                            ui.label("未检测到U盘").classes("text-h5 font-bold text-grey-9 q-ml-sm")
                            ui.space()
                            ui.button(icon="close", on_click=no_device_dialog.close).props(
                                "flat round dense"
                            )

                        with ui.column().classes("items-center py-4 gap-3"):
                            ui.label("请插入U盘后重试").classes("text-body1 text-grey-7")

                            async def refresh():
                                no_device_dialog.close()
                                await start_usb_export()

                            ui.button("刷新", icon="refresh", on_click=refresh).props(
                                "flat no-caps"
                            ).classes("action-button mt-4")

                    no_device_dialog.open()
                    return

                device = devices[0]

                with (
                    ui.dialog() as usb_dialog,
                    ui.card()
                    .classes("dialog-card")
                    .style("width: 550px; padding: 32px; border-radius: 16px;"),
                ):
                    with ui.row().classes("w-full items-center mb-6"):
                        ui.icon("check_circle", size="xl").classes("text-positive")
                        ui.label("检测到U盘").classes("text-h5 font-bold text-grey-9 q-ml-sm")
                        ui.space()
                        ui.button(icon="close", on_click=usb_dialog.close).props("flat round dense")

                    with ui.element("div").classes("info-box"):
                        with ui.row().classes("items-center gap-3 mb-3"):
                            ui.icon("usb", size="lg").classes("text-secondary")
                            ui.label(device.label or "未命名设备").classes(
                                "text-body1 font-semibold"
                            )

                        if device.vendor or device.model:
                            ui.label(f"{device.vendor or ''} {device.model or ''}").classes(
                                "text-sm text-grey-6 mb-2"
                            )

                        ui.element("div").classes("divider")

                        ui.label(f"挂载点: {device.mount_point}").classes(
                            "text-sm text-grey-7 mb-1"
                        )
                        if device.size_bytes:
                            size_gb = device.size_bytes / (1024**3)
                            ui.label(f"容量: {size_gb:.2f} GB").classes("text-sm text-grey-7")

                    with (
                        ui.element("div").classes("export-summary-box mt-4"),
                        ui.row().classes("items-center justify-between"),
                    ):
                        ui.label("会话数量").classes("text-sm text-grey-6")
                        ui.label(f"{len(sessions)} 个").classes("text-body1 font-semibold")

                    async def do_export():
                        export_btn.props("loading")

                        try:
                            session_ids = [s.id for s in sessions]
                            result = await export_service.export_to_usb(session_ids, device)

                            usb_dialog.close()

                            if result.success:
                                ui.notify(
                                    f"成功导出 {result.success_count} 个会话",
                                    type="positive",
                                    position="top",
                                )
                            else:
                                ui.notify(
                                    f"部分失败: 成功 {result.success_count}/{result.total}",
                                    type="warning",
                                    position="top",
                                )

                        except Exception:
                            ui.notify("导出失败", type="negative", position="top")
                        finally:
                            export_btn.props(remove="loading")

                    export_btn = (
                        ui.button("开始导出", on_click=do_export)
                        .props("unelevated color=primary size=lg no-caps")
                        .classes("action-button w-full mt-6")
                        .style("height: 48px;")
                    )

                usb_dialog.open()

            with (
                ui.card()
                .classes("super-card cursor-pointer")
                .on("click", start_usb_export)
                .style(
                    "height: 220px; "
                    "display: flex; "
                    "flex-direction: column; "
                    "padding: 1.5rem; "
                    "box-sizing: border-box;"
                )
            ):
                ui.icon("usb", size="3em").classes("text-secondary rotate-icon").style(
                    "flex-shrink: 0; margin-bottom: 0.75rem;"
                )
                with ui.column().classes("gap-2").style("flex: 1;"):
                    ui.label("U盘导出").classes("text-h6 font-bold text-grey-9")
                    ui.label("直接导出到U盘设备").classes("text-sm text-grey-7")
                ui.button("开始", icon="arrow_forward").props("color=secondary flat dense").classes(
                    "press-button"
                ).style(
                    "align-self: flex-end; "
                    "flex-shrink: 0; "
                    "background: transparent !important; "
                    "box-shadow: none !important;"
                )
