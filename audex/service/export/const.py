from __future__ import annotations


class ErrorMessages:
    """Error messages in Chinese for export service."""

    # Server errors
    SERVER_ALREADY_RUNNING = "服务器已在运行"
    SERVER_START_FAILED = "启动服务器失败"
    SERVER_STOP_FAILED = "停止服务器失败"

    # USB errors
    NO_USB_DEVICE = "未检测到U盘，请插入U盘后重试"
    USB_EXPORT_FAILED = "导出到U盘失败"

    # Session errors
    NO_ACTIVE_SESSION = "登录状态已过期，请重新登录"
