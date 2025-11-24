from __future__ import annotations

from audex.lib.session import SessionManager
from audex.lib.store import Store
from audex.lib.usb import USBManager
from audex.service import BaseService


class ExportService(BaseService):
    def __init__(
        self,
        sm: SessionManager,
        usb: USBManager,
        store: Store,
    ):
        super().__init__(sm=sm)
        self.usb = usb
        self.store = store
