from __future__ import annotations

import asyncio
import contextlib

from audex.helper import net
from audex.lib.cache import KVCache
from audex.lib.exporter import Exporter
from audex.lib.repos.doctor import DoctorRepository
from audex.lib.server import Server
from audex.lib.session import SessionManager
from audex.lib.usb import USBDevice
from audex.lib.usb import USBManager
from audex.service import BaseService
from audex.service.decorators import require_auth
from audex.service.export.const import ErrorMessages
from audex.service.export.exceptions import ExportServiceError
from audex.service.export.exceptions import InternalExportServiceError
from audex.service.export.exceptions import NoUSBDeviceError
from audex.service.export.exceptions import ServerAlreadyRunningError
from audex.service.export.types import ExportResult
from audex.service.export.types import ServerInfo


class ExportService(BaseService):
    """Service for exporting session data via HTTP or USB."""

    __logtag__ = "audex.service.export"

    def __init__(
        self,
        session_manager: SessionManager,
        cache: KVCache,
        doctor_repo: DoctorRepository,
        usb: USBManager,
        exporter: Exporter,
        server: Server,
    ):
        super().__init__(session_manager=session_manager, cache=cache, doctor_repo=doctor_repo)
        self.usb = usb
        self.exporter = exporter
        self.server = server
        self._server_task: asyncio.Task[None] | None = None
        self._server_running = False

    @require_auth
    async def start_server(self) -> ServerInfo:
        """Start HTTP export server.

        Returns:
            ServerInfo with host and port.

        Raises:
            ServerAlreadyRunningError: If server is already running.
            InternalExportServiceError: For internal errors.
        """
        try:
            if self._server_running:
                raise ServerAlreadyRunningError(ErrorMessages.SERVER_ALREADY_RUNNING)

            # Start server in background task
            addr = net.getaddr()
            port = net.getfreeport()
            self._server_task = asyncio.create_task(self.server.start(host="0.0.0.0", port=port))
            self._server_running = True

            # Get server info
            server_info = ServerInfo(
                host=addr,
                port=port,
                url=f"http://{addr}:{port}",
            )

            self.logger.info(f"Started export server at {server_info.url}")
            return server_info

        except ServerAlreadyRunningError:
            raise

        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            raise InternalExportServiceError(ErrorMessages.SERVER_START_FAILED) from e

    @require_auth
    async def stop_server(self) -> None:
        """Stop HTTP export server.

        Raises:
            InternalExportServiceError: For internal errors.
        """
        try:
            if not self._server_running:
                self.logger.warning("Server is not running")
                return

            # Stop server
            await self.server.close()

            # Cancel task if exists
            if self._server_task:
                self._server_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._server_task
                self._server_task = None

            self._server_running = False
            self.logger.info("Stopped export server")

        except Exception as e:
            self.logger.error(f"Failed to stop server: {e}")
            raise InternalExportServiceError(ErrorMessages.SERVER_STOP_FAILED) from e

    @require_auth
    async def is_server_running(self) -> bool:
        """Check if HTTP export server is running."""
        return self._server_running

    @require_auth
    async def list_usb_devices(self) -> list[USBDevice]:
        """List all connected USB storage devices.

        Returns:
            List of connected USB devices.
        """
        try:
            devices = self.usb.list_devices()
            self.logger.debug(f"Found {len(devices)} USB device(s)")
            return devices
        except Exception as e:
            self.logger.error(f"Failed to list USB devices: {e}")
            return []

    @require_auth
    async def export_to_usb(
        self,
        session_ids: list[str],
        device: USBDevice | None = None,
    ) -> ExportResult:
        """Export sessions to USB device.

        Args:
            session_ids: List of session IDs to export.
            device: Target USB device.  If None, uses first available device.

        Returns:
            ExportResult with success status and details.

        Raises:
            NoUSBDeviceError: If no USB device is available.
            InternalExportServiceError: For internal errors.
        """
        try:
            # Get USB device
            if device is None:
                devices = await self.list_usb_devices()
                if not devices:
                    raise NoUSBDeviceError(ErrorMessages.NO_USB_DEVICE)
                device = devices[0]
                self.logger.info(f"Using first USB device: {device.mount_point}")

            # Verify doctor owns all sessions
            session = await self.session_manager.get_session()
            if not session:
                raise ExportServiceError(ErrorMessages.NO_ACTIVE_SESSION)

            for session_id in session_ids:
                sess = await self.exporter.session_repo.read(session_id)
                if not sess or sess.doctor_id != session.doctor_id:
                    raise ExportServiceError(
                        f"无权访问会话 {session_id}",
                    )

            # Export each session
            export_tasks = []

            for session_id in session_ids:
                # Generate ZIP
                zip_data = await self.exporter.export_session_zip(session_id)

                # Get session info for filename
                sess = await self.exporter.session_repo.read(session_id)
                filename = f"{session_id}"
                if sess and sess.patient_name:
                    filename = f"{sess.patient_name}_{session_id}"
                filename += ".zip"

                # Write to temp file
                import pathlib
                import tempfile

                temp_path = pathlib.Path(tempfile.mkdtemp()) / filename
                temp_path.write_bytes(zip_data)

                # Add export task
                self.usb.add_export_task(
                    source=temp_path,
                    dest_name=f"audex_export/{filename}",
                    is_directory=False,
                )
                export_tasks.append((session_id, temp_path))

            # Export to USB
            results = await self.usb.export(device)

            # Clean up temp files
            for _, temp_path in export_tasks:
                try:
                    temp_path.unlink()
                    temp_path.parent.rmdir()
                except Exception:
                    pass

            # Clear export tasks
            self.usb.clear_export_tasks()

            # Check results
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            export_result = ExportResult(
                success=success_count == total_count,
                total=total_count,
                success_count=success_count,
                failed_count=total_count - success_count,
                device_label=device.label or device.mount_point,
            )

            self.logger.info(f"USB export completed: {success_count}/{total_count} successful")

            return export_result

        except (NoUSBDeviceError, ExportServiceError):
            raise
        except Exception as e:
            self.logger.error(f"USB export failed: {e}")
            raise InternalExportServiceError(ErrorMessages.USB_EXPORT_FAILED) from e
