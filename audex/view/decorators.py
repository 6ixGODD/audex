from __future__ import annotations

import functools
import json
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
    return f"""Error Type: {error_info.error_type}
Error Code: {error_info.error_code}
Timestamp: {error_info.timestamp}
Message: {error_info.message}

Technical Details:
{error_info.details}

Stack Trace:
{error_info.traceback}"""


def show_internal_error_dialog(error: InternalError) -> None:
    """Show a modern dialog for internal errors with optimized
    performance."""
    error_info = format_error_info(error)
    error_report = format_error_report(error_info)

    # Use JSON encoding for safe clipboard (faster than manual escaping)
    escaped = json.dumps(error_report)[1:-1]

    # Lighter backdrop without blur for performance
    backdrop = ui.element("div").style(
        "position: fixed; top: 0; left: 0; right: 0; bottom: 0; "
        "background: rgba(0, 0, 0, 0.5); "
        "z-index: 6000; "
        "animation: fadeIn 0.2s ease;"
    )

    # Add animations and button hover effects
    ui.add_head_html("""
    <style>
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    .error-dialog-card {
        animation: slideUp 0.3s ease;
    }
    @keyframes slideUp {
        from { transform: translateY(20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    .error-action-btn {
        transition: all 0.2s ease !important;
    }
    .error-action-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    </style>
    """)

    with ui.dialog() as dialog:
        dialog.props("persistent")

        with (
            ui.card()
            .classes("error-dialog-card")
            .style(
                "width: 560px; max-width: 90vw; padding: 28px; "
                "border-radius: 16px; "
                "box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);"
            )
        ):
            # Header
            with ui.row().classes("w-full items-center mb-6 no-wrap"):
                ui.icon("error_outline", size="xl").classes("text-negative")
                ui.label("出错了").classes("text-h5 font-bold text-grey-9 q-ml-sm")
                ui.space()
                ui.button(icon="close", on_click=lambda: (dialog.close(), backdrop.delete())).props(
                    "flat round dense"
                )

            # Message
            ui.label("系统遇到了一个问题，我们正在努力解决").classes(
                "text-body1 text-grey-8 q-mb-md"
            )

            # Error code badge - styled like original
            with ui.row().classes("items-center gap-2 q-mb-lg"):
                ui.label("错误代码:").classes("text-sm text-grey-7")
                ui.label(f"#{error_info.error_code}").style(
                    "background: #f5f5f5; "
                    "color: #666; "
                    "padding: 6px 12px; "
                    "border-radius: 8px; "
                    "font-family: 'Monaco', 'Menlo', 'Consolas', monospace; "
                    "font-size: 0.875rem; "
                    "font-weight: 600;"
                )

            ui.separator().classes("q-mb-md")

            # Expandable details
            with (
                ui.expansion("查看技术详情", icon="code")
                .classes("w-full")
                .props("dense header-class='bg-grey-2 rounded'"),
                ui.scroll_area().style("max-height: 200px;"),
            ):
                ui.code(error_report).classes("text-xs").style(
                    "background: #f8f9fa; padding: 12px; border-radius: 8px;"
                )

            # Action buttons - original style with hover effects
            with ui.row().classes("w-full gap-3 q-mt-lg justify-end"):
                ui.button(
                    "Copy Details",
                    icon="content_copy",
                    on_click=lambda: (
                        ui.run_javascript(f"navigator.clipboard.writeText('{escaped}')"),
                        ui.notify(
                            "Error details copied", type="positive", position="top", timeout=2000
                        ),
                    ),
                ).props("outline color=grey-8 no-caps").classes("error-action-btn").style(
                    "border-radius: 10px; min-width: 120px; height: 40px; padding: 0 20px;"
                )

                ui.button("Close", on_click=lambda: (dialog.close(), backdrop.delete())).props(
                    "unelevated color=primary no-caps"
                ).classes("error-action-btn").style(
                    "border-radius: 10px; min-width: 120px; height: 40px; padding: 0 20px;"
                )

            # Help hint - grey background with more padding
            with (
                ui.row()
                .classes("w-full items-center gap-2 q-mt-lg")
                .style("background: #f5f5f5; border-radius: 12px; padding: 16px;")
            ):
                ui.icon("lightbulb", size="sm").classes("text-grey-6")
                ui.label("如果问题持续出现，请将错误代码提供给技术支持").classes(
                    "text-sm text-grey-7"
                )

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
        ui.notify(
            "Session expired, please login",
            type="warning",
            position="top",
            timeout=3000,
        )
        ui.navigate.to("/login")
        return

    if isinstance(error, InternalError):
        logger.bind(tag="audex.view.error", **error.as_dict()).exception(
            f"Internal error: {error.message}"
        )
        show_internal_error_dialog(error)

    elif isinstance(error, AudexError):
        show_user_error_notification(error)

    else:
        internal_error = InternalError(
            message="An unexpected error occurred",
            original_error=str(error),
            error_type=error.__class__.__name__,
            traceback="".join(traceback.format_exception(type(error), error, error.__traceback__)),
        )
        logger.bind(tag="audex.view.error", **internal_error.as_dict()).exception(
            f"Unknown error: {error}"
        )
        show_internal_error_dialog(internal_error)


PageMethodT = t.TypeVar("PageMethodT", bound=t.Callable[..., t.Awaitable[None]])


def handle_errors(func: PageMethodT) -> PageMethodT:
    """Decorator to handle exceptions in page render methods."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            handle_exception(e)

    return wrapper
