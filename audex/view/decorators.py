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
    return f"""Error Type: {error_info.error_type}
Error Code: {error_info.error_code}
Timestamp: {error_info.timestamp}
Message: {error_info.message}

Technical Details:
{error_info.details}

Stack Trace:
{error_info.traceback}"""


def show_internal_error_dialog(error: InternalError) -> None:
    """Show a modern dialog for internal errors with unified style."""
    error_info = format_error_info(error)
    error_report = format_error_report(error_info)

    def copy_to_clipboard():
        ui.run_javascript(f"""
            navigator.clipboard.writeText(`{error_report}`).then(() => {{
                console.log('复制成功');
            }}).catch(err => {{
                console.error('复制失败:', err);
            }});
        """)
        ui.notify("错误详情已复制", type="positive", position="top", timeout=2000)

    # Add unified animations and styles
    ui.add_head_html("""
    <style>
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    .error-dialog-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        z-index: 6000;
        animation: fadeIn 0.2s ease;
    }
    .error-dialog-card {
        animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    @keyframes slideUp {
        from { transform: translateY(20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    .error-action-btn {
        border-radius: 12px !  important;
        font-size: 16px !important;
        font-weight: 500 ! important;
        letter-spacing: 0.02em !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        min-width: 120px !important;
        height: 44px !important;
        text-transform: none !important;
    }
    .error-action-btn:hover {
        transform: translateY(-2px);
    }
    .error-action-btn:active {
        transform: translateY(0);
    }
    .error-btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.25), 0 2px 8px rgba(118, 75, 162, 0.15) !important;
    }
    .error-btn-primary:hover {
        background: linear-gradient(135deg, #7c8ef0 0%, #8a5db0 100%) !important;
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.35), 0 4px 12px rgba(118, 75, 162, 0.25) !important;
    }
    .error-btn-secondary {
        background: rgba(248, 249, 250, 0.8) !important;
        color: #6b7280 !important;
        border: 1px solid rgba(0, 0, 0, 0.08) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
    }
    .error-btn-secondary:hover {
        background: rgba(243, 244, 246, 0.9) !important;
        border-color: rgba(0, 0, 0, 0.12) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
    }
    .error-code-badge {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        color: #667eea;
        padding: 8px 16px;
        border-radius: 12px;
        font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
        font-size: 0.875rem;
        font-weight: 600;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    .error-help-box {
        background: linear-gradient(135deg, #f8f9fa 0%, #f5f6f7 100%);
        border-radius: 12px;
        padding: 16px;
        border: 1px solid rgba(0, 0, 0, 0.06);
    }
    </style>
    """)

    # Backdrop
    backdrop = ui.element("div").classes("error-dialog-backdrop")

    with ui.dialog() as dialog:
        dialog.props("persistent")

        with (
            ui.card()
            .classes("error-dialog-card")
            .style(
                "width: 560px; max-width: 90vw; padding: 32px; "
                "border-radius: 20px; "
                "box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 8px 24px rgba(0, 0, 0, 0.1);"
            )
        ):
            # Header
            with ui.row().classes("w-full items-center mb-6 no-wrap"):
                ui.icon("error_outline", size="xl").classes("text-negative")
                ui.label("出错了").classes("text-h5 font-bold text-grey-9").style(
                    "margin-left: 12px;"
                )
                ui.space()
                ui.button(icon="close", on_click=lambda: (dialog.close(), backdrop.delete())).props(
                    "flat round dense"
                ).style("margin: -8px;")

            # Message
            ui.label("系统遇到了一个问题，我们正在努力解决").classes(
                "text-body1 text-grey-8"
            ).style("margin-bottom: 20px;")

            # Error code badge
            with ui.row().classes("items-center gap-2").style("margin-bottom: 24px;"):
                ui.label("错误代码:").classes("text-sm text-grey-7")
                ui.html(
                    f'<div class="error-code-badge">#{error_info.error_code}</div>', sanitize=False
                )

            ui.separator().style("margin-bottom: 20px; background: rgba(0, 0, 0, 0.06);")

            # Expandable details
            with (
                ui.expansion("查看技术详情", icon="code")
                .classes("w-full")
                .style(
                    "background: rgba(248, 249, 250, 0.5); "
                    "border-radius: 12px; "
                    "border: 1px solid rgba(0, 0, 0, 0.06);"
                ),
                ui.scroll_area().style("max-height: 200px;"),
            ):
                ui.code(error_report).classes("text-xs").style(
                    "background: #f8f9fa; "
                    "padding: 16px; "
                    "border-radius: 8px; "
                    "font-family: 'Monaco', 'Menlo', 'Consolas', monospace;"
                )

            # Action buttons
            with ui.row().classes("w-full gap-3 justify-end").style("margin-top: 24px;"):
                ui.button(
                    "复制详情",
                    icon="content_copy",
                    on_click=copy_to_clipboard,  # 修改这里
                ).props("no-caps").classes("error-action-btn error-btn-secondary")

                ui.button("关闭", on_click=lambda: (dialog.close(), backdrop.delete())).props(
                    "unelevated no-caps"
                ).classes("error-action-btn error-btn-primary")

            # Help hint
            with (
                ui.element("div").classes("error-help-box").style("margin-top: 20px;"),
                ui.row().classes("items-center gap-2"),
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
