from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.lib.usb import USBManager


def make_usb_manager() -> USBManager:
    from audex.lib.usb import USBManager

    return USBManager()
