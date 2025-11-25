from __future__ import annotations

import functools
import traceback
import typing as t

from loguru import logger
from nicegui import ui

from audex.exceptions import AudexError
from audex.exceptions import InternalError
from audex.exceptions import PermissionDeniedError
from audex.utils import utcnow


class ErrorInfo(t.NamedTuple):
    """Error information for display."""

    error_type: str
    error_code: int
    message: str
    timestamp: str
    traceback: str
    details: dict[str, t.Any]


def format_error_info(error: Exception) -> ErrorInfo:
    """Format exception into ErrorInfo."""
    timestamp = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    if isinstance(error, AudexError):
        error_type = error.__class__.__name__
        error_code = error.code
        message = error.message
        details = error.as_dict()
    else:
        error_type = error.__class__.__name__
        error_code = 0
        message = str(error)
        details = {}

    return ErrorInfo(
        error_type=error_type,
        error_code=error_code,
        message=message,
        timestamp=timestamp,
        traceback=tb,
        details=details,
    )


def format_error_report(error_info: ErrorInfo) -> str:
    """Format error report text for copying."""
    return f"""
错误类型: {error_info.error_type}
错误代码: {error_info.error_code}
发生时间: {error_info.timestamp}
错误信息: {error_info.message}

技术详情:
{error_info.details}

堆栈追踪:
{error_info.traceback}
"""


def show_internal_error_dialog(error: InternalError) -> None:
    """Show a dialog for internal errors with copy/screenshot
    support."""
    error_info = format_error_info(error)
    error_report = format_error_report(error_info)

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
        # Header
        with ui.row().classes("w-full items-center justify-between mb-4"):
            ui.icon("error", size="2em").classes("text-negative")
            ui.label("系统错误").classes("text-h5 text-negative")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense")

        ui.separator()

        # Error message
        with ui.card().classes("w-full bg-negative-1 mb-4"):
            ui.label("抱歉，系统遇到了内部错误").classes("text-subtitle1 mb-2")
            ui.label(f"错误代码: {error_info.error_code}").classes(
                "text-body2 text-grey-8 font-mono"
            )
            ui.label(f"发生时间: {error_info.timestamp}").classes("text-caption text-grey-7")

        # Instructions
        ui.label("请将以下错误信息提供给管理员：").classes("text-subtitle2 mb-2")

        # Error details (expandable)
        with (
            ui.expansion("查看详细信息", icon="info").classes("w-full"),
            ui.scroll_area().classes("w-full h-64"),
        ):
            ui.code(error_report).classes("text-xs")

        # Action buttons
        with ui.row().classes("w-full justify-end gap-2 mt-4"):

            async def copy_error_info():
                """Copy error info to clipboard."""
                # Escape backticks in error report
                escaped_report = error_report.replace("`", "\\`").replace("$", "\\$")
                await ui.run_javascript(f"navigator.clipboard.writeText(`{escaped_report}`)")
                ui.notify("错误信息已复制到剪贴板", type="positive")

            ui.button(
                "复制错误信息",
                icon="content_copy",
                on_click=copy_error_info,
            ).props("outline")

            ui.button("关闭", on_click=dialog.close).props("color=primary")

        # Screenshot hint
        with ui.card().classes("w-full bg-info-1 mt-4"), ui.row().classes("items-center gap-2"):
            ui.icon("camera_alt").classes("text-info")
            ui.label("提示：您也可以直接截图此窗口发送给管理员").classes("text-caption")

    dialog.open()


def show_user_error_notification(error: AudexError) -> None:
    """Show a simple notification for user-facing errors."""
    ui.notify(
        error.message,
        type="negative",
        position="top",
        close_button=True,
        timeout=5000,
    )


def handle_exception(error: Exception) -> None:
    """Handle exception and display appropriate UI feedback."""
    if isinstance(error, PermissionDeniedError):
        # Redirect to login page for permission errors
        ui.notify(
            "权限不足，请登录以继续",
            type="warning",
            position="top",
            close_button=True,
            timeout=3000,
        )
        ui.navigate.to("/login")
        return

    if isinstance(error, InternalError):
        # Internal errors: log and show detailed dialog
        logger.bind(tag="audex.view.error", **error.as_dict()).error(
            f"Internal error: {error.message}"
        )
        show_internal_error_dialog(error)

    elif isinstance(error, AudexError):
        # User-facing errors: show simple notification
        show_user_error_notification(error)

    else:
        # Unknown errors: treat as internal
        internal_error = InternalError(
            message="Unknown system error occurred",
            original_error=str(error),
            error_type=error.__class__.__name__,
            traceback="".join(traceback.format_exception(type(error), error, error.__traceback__)),
        )
        logger.bind(tag="audex.view.error", **internal_error.as_dict()).error(
            f"Unknown error: {error}", exc_info=True
        )
        show_internal_error_dialog(internal_error)


PageMethodT = t.TypeVar("PageMethodT", bound=t.Callable[..., t.Awaitable[None]])


def handle_errors(func: PageMethodT) -> PageMethodT:
    """Decorator to handle exceptions in page render methods.

    This decorator catches all exceptions during page rendering and
    displays them appropriately:
    - InternalError: Shows detailed error dialog with copy functionality
    - AudexError: Shows simple notification with user-friendly message
    - Other exceptions: Treats as internal error

    Args:
        func: The page render function to wrap.

    Returns:
        Wrapped function with error handling.

    Example:
        ```python
        class LoginPage(Page):
            @handle_errors
            async def render(self) -> None:
                # Any exception here will be caught and displayed
                await self.doctor_service.login(...)
        ```
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            handle_exception(e)
            # Don't re-raise, error is already displayed to user

    return wrapper
