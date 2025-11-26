from __future__ import annotations

import typing as t


class ServerInfo(t.NamedTuple):
    """HTTP server information."""

    host: str
    port: int
    url: str


class ExportResult(t.NamedTuple):
    """Result of USB export operation."""

    success: bool
    total: int
    success_count: int
    failed_count: int
    device_label: str
