from __future__ import annotations

import asyncio
import typing as t

from nicegui import ui

from audex.lib.filesys import ClearResult
from audex.lib.filesys import FileSystemManager
from audex.lib.filesys.exceptions import ClearOperationError
from audex.lib.filesys.exceptions import DirectoryNotFoundError
from audex.lib.filesys.exceptions import FileSystemError
from audex.lib.filesys.exceptions import PartialClearError


class FileSystemIndicator:
    """File system status indicator component."""

    def __init__(self, filesys_manager: FileSystemManager) -> None:
        self.filesys_manager = filesys_manager
        self.icon_display: ui.button | None = None

        # Dialog state
        self.dialog: ui.dialog | None = None
        self.info_container: ui.column | None = None
        self.loading = False

    def render(self) -> ui.button:
        """Render filesystem indicator as a simple icon button."""
        self.icon_display = (
            ui.button(icon="storage", on_click=self._show_dialog)
            .props("flat round")
            .classes("filesys-indicator-btn text-grey-6")
            .tooltip("存储管理")
        )

        return self.icon_display

    def _show_dialog(self) -> None:
        """Show filesystem management dialog."""
        with (
            ui.dialog() as dialog,
            ui.card()
            .classes("filesys-dialog-card")
            .style(
                "width: 680px; max-width: 95vw; padding: 36px; "
                "border-radius: 24px; background: white; "
                "box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08), 0 8px 24px rgba(0, 0, 0, 0.04);"
            ),
        ):
            self.dialog = dialog

            # Header
            with ui.row().classes("items-center justify-between w-full mb-8"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("storage", size="lg").classes("text-primary")
                    ui.label("存储管理").classes("text-h5 font-bold text-grey-9")
                ui.button(icon="close", on_click=dialog.close).props("flat round").style(
                    "border-radius: 50%;"
                )

            # Loading overlay
            loading_container = ui.column().classes("w-full items-center gap-3 py-8")
            with loading_container:
                ui.spinner(size="lg").classes("text-primary")
                ui.label("正在加载存储信息...").classes("text-body2 text-grey-7")

            # Info container
            self.info_container = ui.column().classes("w-full gap-6").style("display: none;")

            # Load data in background
            async def load_info():
                await self._refresh_info()
                loading_container.style("display: none;")
                if self.info_container:
                    self.info_container.style("display: flex;")

            asyncio.create_task(load_info())  # noqa

        dialog.open()

    async def _refresh_info(self) -> None:
        """Refresh filesystem information display."""
        if not self.info_container:
            return

        self.info_container.clear()

        try:
            store_path = self.filesys_manager.get_store_path()
            disk_usage = self.filesys_manager.get_disk_usage()
            store_info = await self.filesys_manager.get_directory_info(store_path)
            logs_info = await self.filesys_manager.get_logs_info()
            mount_point = self.filesys_manager.get_mount_point()

            with self.info_container:
                # Main layout: left (disk ring) + right (store + logs)
                with ui.row().classes("w-full gap-6"):
                    # Left: Disk usage ring chart
                    with (
                        ui.column().classes("items-center justify-center").style("flex: 0 0 240px;")
                    ):
                        # Ring chart container
                        ring_size = 180
                        stroke_width = 18
                        radius = (ring_size - stroke_width) / 2
                        circumference = 2 * 3.14159 * radius
                        used_percent = disk_usage.percent
                        offset = circumference * (1 - used_percent / 100)

                        # Determine color
                        if used_percent > 90:
                            color = "#ef4444"
                        elif used_percent > 75:
                            color = "#f59e0b"
                        else:
                            color = "#10b981"

                        with (
                            ui.element("div")
                            .classes("items-center justify-center")
                            .style(
                                f"position: relative; width: {ring_size}px; height: {ring_size}px;"
                            )
                        ):
                            # SVG ring
                            ui.html(
                                f"""
                                <svg width="{ring_size}" height="{ring_size}" style="transform: rotate(-90deg);">
                                    <!-- Background circle -->
                                    <circle
                                        cx="{ring_size / 2}"
                                        cy="{ring_size / 2}"
                                        r="{radius}"
                                        fill="none"
                                        stroke="#e5e7eb"
                                        stroke-width="{stroke_width}"
                                    />
                                    <!-- Progress circle -->
                                    <circle
                                        cx="{ring_size / 2}"
                                        cy="{ring_size / 2}"
                                        r="{radius}"
                                        fill="none"
                                        stroke="{color}"
                                        stroke-width="{stroke_width}"
                                        stroke-dasharray="{circumference}"
                                        stroke-dashoffset="{offset}"
                                        stroke-linecap="round"
                                        style="transition: stroke-dashoffset 0.5s ease;"
                                    />
                                </svg>
                                """
                            )

                            # Center text
                            with (
                                ui.column()
                                .classes("items-center justify-center absolute")
                                .style("top: 50%; left: 50%; transform: translate(-50%, -50%);")
                            ):
                                ui.label(f"{used_percent}%").classes("text-h4 font-bold").style(
                                    f"color: {color};"
                                )
                                ui.label("已使用").classes("text-xs text-grey-6")

                        # Disk info below ring
                        with ui.column().classes("items-center gap-2 mt-4 w-full"):
                            ui.label(mount_point).classes("text-sm font-semibold text-grey-8")

                            with ui.column().classes("items-center gap-1"):
                                ui.label(
                                    self.filesys_manager.format_bytes(disk_usage.free)
                                ).classes("text-body2 font-bold text-positive")
                                ui.label("可用空间").classes("text-xs text-grey-6")

                    # Right: Store and Logs cards
                    with ui.column().classes("gap-4").style("flex: 1;"):
                        # Store card
                        with (
                            ui.card()
                            .classes("w-full")
                            .style(
                                "padding: 20px; background: white; border-radius: 16px; "
                                "box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);"
                            )
                        ):
                            with ui.row().classes("items-center gap-2 mb-3"):
                                ui.icon("folder", size="md").classes("text-primary")
                                ui.label("存储目录").classes(
                                    "text-subtitle1 font-semibold text-grey-8"
                                )

                            with ui.column().classes("gap-2 mb-3"):
                                with ui.row().classes("items-center justify-between w-full"):
                                    ui.label("文件数").classes("text-xs text-grey-6")
                                    ui.label(f"{store_info.file_count} 个").classes(
                                        "text-body2 font-bold text-grey-9"
                                    )

                                with ui.row().classes("items-center justify-between w-full"):
                                    ui.label("占用空间").classes("text-xs text-grey-6")
                                    ui.label(
                                        self.filesys_manager.format_bytes(store_info.size)
                                    ).classes("text-body2 font-bold text-grey-9")

                            # Clear store button (full width)
                            async def clear_store_confirm():
                                await self._show_clear_confirm(
                                    title="清空存储目录",
                                    items=[
                                        f"文件数量: {store_info.file_count} 个",
                                        f"释放空间: {self.filesys_manager.format_bytes(store_info.size)}",
                                    ],
                                    action=self._do_clear_store,
                                    color="primary",
                                )

                            ui.button(
                                "清空存储",
                                icon="delete_sweep",
                                on_click=clear_store_confirm,
                            ).props("outline color=primary no-caps").classes("w-full").style(
                                "border-radius: 50px; height: 40px;"
                            )

                        # Logs card
                        with (
                            ui.card()
                            .classes("w-full")
                            .style(
                                "padding: 20px; background: white; border-radius: 16px; "
                                "box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);"
                            )
                        ):
                            with ui.row().classes("items-center gap-2 mb-3"):
                                ui.icon("description", size="md").classes("text-secondary")
                                ui.label("日志文件").classes(
                                    "text-subtitle1 font-semibold text-grey-8"
                                )

                            with ui.column().classes("gap-2 mb-3"):
                                with ui.row().classes("items-center justify-between w-full"):
                                    ui.label("文件数").classes("text-xs text-grey-6")
                                    ui.label(f"{logs_info.file_count} 个").classes(
                                        "text-body2 font-bold text-grey-9"
                                    )

                                with ui.row().classes("items-center justify-between w-full"):
                                    ui.label("占用空间").classes("text-xs text-grey-6")
                                    ui.label(
                                        self.filesys_manager.format_bytes(logs_info.size)
                                    ).classes("text-body2 font-bold text-grey-9")

                            # Clear logs button (full width)
                            async def clear_logs_confirm():
                                await self._show_clear_confirm(
                                    title="清空日志文件",
                                    items=[
                                        f"文件数量: {logs_info.file_count} 个",
                                        f"释放空间: {self.filesys_manager.format_bytes(logs_info.size)}",
                                    ],
                                    action=self._do_clear_logs,
                                    color="secondary",
                                )

                            ui.button(
                                "清空日志",
                                icon="delete_sweep",
                                on_click=clear_logs_confirm,
                            ).props("outline color=secondary no-caps").classes("w-full").style(
                                "border-radius: 50px; height: 40px;"
                            )

                # Separator
                ui.separator().classes("my-2")

                # Danger zone - Clear All (full width button)
                total_files = store_info.file_count + logs_info.file_count
                total_space = store_info.size + logs_info.size

                async def clear_all_confirm():
                    await self._show_clear_confirm(
                        title="清空所有数据",
                        items=[
                            f"存储文件: {store_info.file_count} 个 ({self.filesys_manager.format_bytes(store_info.size)})",
                            f"日志文件: {logs_info.file_count} 个 ({self.filesys_manager.format_bytes(logs_info.size)})",
                            f"总计: {total_files} 个文件",
                            f"总释放空间: {self.filesys_manager.format_bytes(total_space)}",
                        ],
                        action=self._do_clear_all,
                        color="negative",
                        dangerous=True,
                    )

                ui.button(
                    "清空所有数据",
                    icon="delete_forever",
                    on_click=clear_all_confirm,
                ).props("unelevated color=negative no-caps").classes("w-full").style(
                    "border-radius: 50px; height: 48px; font-size: 15px; font-weight: 600;"
                )

        except FileSystemError as e:
            if self.info_container:
                self.info_container.clear()
                with self.info_container, ui.column().classes("items-center gap-3 py-8"):
                    ui.icon("error_outline", size="xl").classes("text-negative")
                    ui.label(f"加载失败: {e}").classes("text-body2 text-negative")

    async def _show_clear_confirm(
        self,
        title: str,
        items: list[str],
        action: t.Callable[[], t.Awaitable[None]],
        color: str = "negative",
        dangerous: bool = False,
    ) -> None:
        """Show confirmation dialog for clear operations."""
        with (
            ui.dialog() as confirm_dialog,
            ui.card().style(
                "width: 480px; max-width: 90vw; padding: 32px; "
                "border-radius: 20px; background: white; "
                "box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12);"
            ),
        ):
            # Header
            with ui.row().classes("w-full items-center mb-6"):
                ui.icon("warning" if dangerous else "info", size="xl").classes(f"text-{color}")
                ui.label(title).classes("text-h5 font-bold text-grey-9 ml-3 flex-1")
                ui.button(icon="close", on_click=confirm_dialog.close).props("flat round").style(
                    "border-radius: 50%;"
                )

            # Info items
            ui.label("此操作将：").classes("text-sm text-grey-7 font-medium mb-2")

            with ui.column().classes("gap-2 mb-4 ml-2"):
                for item in items:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("check_circle", size="sm").classes(f"text-{color}")
                        ui.label(item).classes("text-body2 text-grey-8")

            if dangerous:
                with (
                    ui.element("div")
                    .classes("w-full")
                    .style(
                        "padding: 12px 16px; background: rgba(239, 68, 68, 0.08); "
                        "border-radius: 12px; border-left: 4px solid #ef4444;"
                    )
                ):
                    ui.label("⚠️ 此操作不可恢复！").classes("text-body2 text-negative font-bold")

            # Buttons
            with ui.row().classes("w-full gap-3 justify-end mt-6"):
                ui.button("取消", on_click=confirm_dialog.close).props(
                    "outline color=grey-8 no-caps"
                ).style("min-width: 100px; border-radius: 50px; height: 44px;")

                async def do_action():
                    confirm_dialog.close()
                    await action()

                ui.button("确认清空", on_click=do_action).props(
                    f"unelevated color={color} no-caps"
                ).style("min-width: 100px; border-radius: 50px; height: 44px; font-weight: 600;")

        confirm_dialog.open()

    async def _do_clear_store(self) -> None:
        """Execute clear store operation."""
        ui.notify("正在清空存储目录...", type="info", position="top")

        try:
            result: ClearResult = await self.filesys_manager.clear_store()

            message = (
                f"✓ 存储目录已清空\n"
                f"删除文件: {result.files_cleared} 个\n"
                f"释放空间: {self.filesys_manager.format_bytes(result.space_freed)}"
            )
            ui.notify(message, type="positive", position="top", timeout=5000)
            await self._refresh_info()

        except DirectoryNotFoundError as e:
            ui.notify(f"✗ 目录不存在: {e.path}", type="warning", position="top")

        except PartialClearError as e:
            message = (
                f"⚠ 部分清空成功\n"
                f"成功: {e.succeeded_count} 个\n"
                f"失败: {e.failed_count} 个\n"
                f"释放空间: {self.filesys_manager.format_bytes(e.space_freed)}"
            )
            ui.notify(message, type="warning", position="top", timeout=5000)
            await self._refresh_info()

        except ClearOperationError as e:
            ui.notify(
                f"✗ 清空失败: {e.operation} - {e.original_error}",
                type="negative",
                position="top",
            )

        except FileSystemError as e:
            ui.notify(f"✗ 操作失败: {e}", type="negative", position="top")

    async def _do_clear_logs(self) -> None:
        """Execute clear logs operation."""
        ui.notify("正在清空日志文件...", type="info", position="top")

        try:
            result: ClearResult = await self.filesys_manager.clear_logs()

            message = (
                f"✓ 日志文件已清空\n"
                f"清空文件: {result.files_cleared} 个\n"
                f"释放空间: {self.filesys_manager.format_bytes(result.space_freed)}"
            )
            ui.notify(message, type="positive", position="top", timeout=5000)
            await self._refresh_info()

        except PartialClearError as e:
            message = (
                f"⚠ 部分清空成功\n"
                f"成功: {e.succeeded_count} 个\n"
                f"失败: {e.failed_count} 个\n"
                f"释放空间: {self.filesys_manager.format_bytes(e.space_freed)}"
            )
            ui.notify(message, type="warning", position="top", timeout=5000)
            await self._refresh_info()

        except ClearOperationError as e:
            ui.notify(
                f"✗ 清空失败: {e.operation} - {e.original_error}",
                type="negative",
                position="top",
            )

        except FileSystemError as e:
            ui.notify(f"✗ 操作失败: {e}", type="negative", position="top")

    async def _do_clear_all(self) -> None:
        """Execute clear all operation."""
        ui.notify("正在清空所有数据...", type="info", position="top")

        try:
            store_result, logs_result = await self.filesys_manager.clear_all()
            total_space = store_result.space_freed + logs_result.space_freed

            message = (
                f"✓ 所有数据已清空\n"
                f"存储文件: {store_result.files_cleared} 个 ({self.filesys_manager.format_bytes(store_result.space_freed)})\n"
                f"日志文件: {logs_result.files_cleared} 个 ({self.filesys_manager.format_bytes(logs_result.space_freed)})\n"
                f"总释放空间: {self.filesys_manager.format_bytes(total_space)}"
            )
            ui.notify(message, type="positive", position="top", timeout=6000)
            await self._refresh_info()

        except PartialClearError as e:
            message = (
                f"⚠ 部分清空成功\n"
                f"成功: {e.succeeded_count} 个\n"
                f"失败: {e.failed_count} 个\n"
                f"释放空间: {self.filesys_manager.format_bytes(e.space_freed)}\n"
                f"失败项: {len(e.failed_items)} 个"
            )
            ui.notify(message, type="warning", position="top", timeout=6000)
            await self._refresh_info()

        except ClearOperationError as e:
            ui.notify(
                f"✗ 清空失败: {e.operation} - {e.original_error}",
                type="negative",
                position="top",
            )

        except FileSystemError as e:
            ui.notify(f"✗ 操作失败: {e}", type="negative", position="top")
