from __future__ import annotations

import typing as t

from audex.exceptions import AudexError
from audex.exceptions import InternalError


class ExportServiceError(AudexError):
    """Base exception for export service errors."""

    default_message = "Export service error"
    code: t.ClassVar[int] = 0x50


class InternalExportServiceError(InternalError):
    """Internal error in export service."""

    default_message = "Internal export service error"
    code: t.ClassVar[int] = 0x51


class NoUSBDeviceError(ExportServiceError):
    """Raised when no USB device is available."""

    default_message = "No USB device available"
    code: t.ClassVar[int] = 0x52


class ServerAlreadyRunningError(ExportServiceError):
    """Raised when server is already running."""

    default_message = "Server already running"
    code: t.ClassVar[int] = 0x53
