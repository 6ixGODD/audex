from __future__ import annotations

import abc
import asyncio
import contextlib
import os
import pathlib
import platform
import shutil
import typing as t

from audex.helper.mixin import AsyncLifecycleMixin
from audex.helper.mixin import LoggingMixin


class USBDevice(t.NamedTuple):
    """Represents a USB storage device.

    Attributes:
        device_node: Device node path (e.g., /dev/sdb1 on Linux, E: on Windows).
        mount_point: Where the device is mounted (e.g., /media/usb or E:\\).
        label: Volume label of the device.
        fs_type: Filesystem type (e.g., vfat, exfat, ntfs).
        size_bytes: Total size in bytes.
        vendor: Device vendor name.
        model: Device model name.
    """

    device_node: str
    mount_point: str
    label: str | None
    fs_type: str | None
    size_bytes: int | None
    vendor: str | None
    model: str | None


class USBExportTask(t.NamedTuple):
    """Represents a file/directory export task.

    Attributes:
        source: Source file or directory path.
        dest_name: Destination name (relative to USB root).
        is_directory: Whether the source is a directory.
    """

    source: pathlib.Path
    dest_name: str
    is_directory: bool


class USBBackend(abc.ABC):
    """Abstract base class for USB device backends."""

    def __init__(self, logger: t.Any) -> None:
        self.logger = logger

    @abc.abstractmethod
    def list_devices(self) -> list[USBDevice]:
        """List all currently connected USB storage devices."""

    @abc.abstractmethod
    async def start_monitoring(self, callback: t.Callable[[str, t.Any], None]) -> None:
        """Start monitoring for USB device events."""

    @abc.abstractmethod
    async def stop_monitoring(self) -> None:
        """Stop monitoring for USB device events."""


class LinuxUSBBackend(USBBackend):
    """Linux USB backend using pyudev."""

    def __init__(self, logger: t.Any) -> None:
        super().__init__(logger)
        try:
            import pyudev

            self._pyudev = pyudev
            self._context = pyudev.Context()
            self._monitor: pyudev.Monitor | None = None
            self._observer: pyudev.MonitorObserver | None = None
        except ImportError as e:
            raise RuntimeError(
                "pyudev is required for Linux USB support. Install it with: pip install pyudev"
            ) from e

    def list_devices(self) -> list[USBDevice]:
        """List all currently connected USB storage devices."""
        devices: list[USBDevice] = []

        for device in self._context.list_devices(subsystem="block", DEVTYPE="partition"):
            if device.find_parent("usb") is None:
                continue

            mount_point = self._get_mount_point(device.device_node)
            if not mount_point:
                continue

            id_vendor = device.get("ID_VENDOR", "Unknown")
            id_model = device.get("ID_MODEL", "Unknown")
            id_fs_type = device.get("ID_FS_TYPE")
            id_fs_label = device.get("ID_FS_LABEL")

            size_bytes = None
            size_file = pathlib.Path(f"/sys/class/block/{device.sys_name}/size")
            if size_file.exists():
                try:
                    sectors = int(size_file.read_text().strip())
                    size_bytes = sectors * 512
                except (ValueError, OSError):
                    pass

            usb_device = USBDevice(
                device_node=device.device_node,
                mount_point=mount_point,
                label=id_fs_label,
                fs_type=id_fs_type,
                size_bytes=size_bytes,
                vendor=id_vendor,
                model=id_model,
            )
            devices.append(usb_device)
            self.logger.debug(f"Found USB device: {usb_device}")

        return devices

    def _get_mount_point(self, device_node: str) -> str | None:
        """Get the mount point for a device node."""
        try:
            with pathlib.Path("/proc/mounts").open("r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == device_node:
                        return parts[1]
        except OSError as e:
            self.logger.warning(f"Failed to read /proc/mounts: {e}")

        return None

    async def start_monitoring(self, callback: t.Callable[[str, t.Any], None]) -> None:
        """Start monitoring for USB device events."""
        self._monitor = self._pyudev.Monitor.from_netlink(self._context)
        self._monitor.filter_by(subsystem="block")

        self._observer = self._pyudev.MonitorObserver(self._monitor, callback)
        self._observer.start()
        self.logger.debug("Started Linux USB monitoring")

    async def stop_monitoring(self) -> None:
        """Stop monitoring for USB device events."""
        if self._observer:
            self._observer.stop()
            self._observer = None

        self._monitor = None
        self.logger.debug("Stopped Linux USB monitoring")


class WindowsUSBBackend(USBBackend):
    """Windows USB backend using win32api and WMI."""

    def __init__(self, logger: t.Any) -> None:
        super().__init__(logger)
        try:
            import win32api
            import win32file
            import wmi

            self._win32api = win32api
            self._win32file = win32file
            self._wmi = wmi
            self._wmi_connection = wmi.WMI()
            self._monitoring = False
            self._monitor_task: asyncio.Task[None] | None = None
        except ImportError as e:
            raise RuntimeError(
                "pywin32 and WMI are required for Windows USB support. "
                "Install them with: pip install pywin32 wmi"
            ) from e

    def list_devices(self) -> list[USBDevice]:
        """List all currently connected USB storage devices."""
        devices: list[USBDevice] = []

        # Get all removable drives
        drive_types = self._win32api.GetLogicalDriveStrings()
        drives = [d for d in drive_types.split("\x00") if d]

        for drive in drives:
            try:
                drive_type = self._win32file.GetDriveType(drive)
                # DRIVE_REMOVABLE = 2
                if drive_type != 2:
                    continue

                # Get drive information
                try:
                    volume_info = self._win32api.GetVolumeInformation(drive)
                    label = volume_info[0]
                    fs_type = volume_info[4]
                except Exception:
                    label = None
                    fs_type = None

                # Get drive size
                size_bytes = None
                try:
                    _, total_bytes, _ = self._win32api.GetDiskFreeSpaceEx(drive)
                    size_bytes = total_bytes
                except Exception:
                    pass

                # Try to get vendor and model from WMI
                vendor = None
                model = None
                try:
                    for disk in self._wmi_connection.Win32_DiskDrive():
                        if disk.MediaType == "Removable Media":
                            for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                                for logical_disk in partition.associators(
                                    "Win32_LogicalDiskToPartition"
                                ):
                                    if logical_disk.DeviceID == drive.rstrip("\\"):
                                        vendor = disk.Manufacturer
                                        model = disk.Model
                                        break
                except Exception:
                    pass

                device_node = drive.rstrip("\\")
                mount_point = drive

                usb_device = USBDevice(
                    device_node=device_node,
                    mount_point=mount_point,
                    label=label,
                    fs_type=fs_type,
                    size_bytes=size_bytes,
                    vendor=vendor,
                    model=model,
                )
                devices.append(usb_device)
                self.logger.debug(f"Found USB device: {usb_device}")

            except Exception as e:
                self.logger.warning(f"Error checking drive {drive}: {e}")
                continue

        return devices

    async def start_monitoring(self, callback: t.Callable[[str, t.Any], None]) -> None:
        """Start monitoring for USB device events using WMI."""
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(callback))
        self.logger.debug("Started Windows USB monitoring")

    async def stop_monitoring(self) -> None:
        """Stop monitoring for USB device events."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task
            self._monitor_task = None
        self.logger.debug("Stopped Windows USB monitoring")

    async def _monitor_loop(self, callback: t.Callable[[str, t.Any], None]) -> None:
        """Monitor loop for Windows USB events."""
        # Watch for Win32_VolumeChangeEvent
        watcher = self._wmi_connection.Win32_VolumeChangeEvent.watch_for(
            notification_type="Creation",
            delay_secs=1,
        )

        while self._monitoring:
            try:
                # Check for events (non-blocking with timeout)
                await asyncio.sleep(1)

                # Poll for new devices
                try:
                    event = watcher(timeout_ms=100)
                    if event and event.EventType == 2:  # Event types: 2=inserted, 3=removed
                        self.logger.info("USB device connected (Windows)")
                        # Create a simple device object for callback
                        callback("add", {"device_type": "volume"})
                except Exception:
                    # Timeout or no event
                    pass

            except Exception as e:
                self.logger.error(f"Error in Windows USB monitor loop: {e}")
                await asyncio.sleep(5)


class USBManager(LoggingMixin, AsyncLifecycleMixin):
    """Cross-platform USB storage device manager for file export.

    This manager monitors USB device connections and provides functionality
    to export files and directories to connected USB drives. It automatically
    selects the appropriate backend (Linux/Windows) based on the platform.

    Example:
        ```python
        # Create manager
        manager = USBManager()

        # Add export tasks
        manager.add_export_task(
            source="/var/log/app.log",
            dest_name="logs/app.log",
        )
        manager.add_export_task(
            source="/data/recordings",
            dest_name="recordings",
            is_directory=True,
        )

        # Start monitoring
        await manager.start()

        # Export to specific device manually
        devices = manager.list_devices()
        if devices:
            await manager.export(devices[0])

        # Stop monitoring
        await manager.stop()
        ```
    """

    __logtag__ = "audex.lib.usb.manager"

    def __init__(self) -> None:
        super().__init__()
        self.export_tasks: list[USBExportTask] = []

        # Initialize platform-specific backend
        system = platform.system()
        if system == "Linux":
            self._backend: USBBackend = LinuxUSBBackend(self.logger)
            self.logger.info("Initialized Linux USB backend")
        elif system == "Windows":
            self._backend = WindowsUSBBackend(self.logger)
            self.logger.info("Initialized Windows USB backend")
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

        self._running = False

    def add_export_task(
        self,
        source: str | pathlib.Path | os.PathLike[str],
        dest_name: str,
        *,
        is_directory: bool = False,
    ) -> None:
        """Add a file or directory to export when USB is connected.

        Args:
            source: Source file or directory path.
            dest_name: Destination name on USB (e.g., "logs/app.log" or "data").
            is_directory: Whether the source is a directory.

        Example:
            ```python
            # Export single file
            manager.add_export_task(
                source="/var/log/app.log",
                dest_name="logs/app.log",
            )

            # Export directory
            manager.add_export_task(
                source="/data/sessions",
                dest_name="sessions",
                is_directory=True,
            )
            ```
        """
        source_path = pathlib.Path(source)
        if not source_path.exists():
            self.logger.warning(f"Source path does not exist: {source_path}")

        task = USBExportTask(
            source=source_path,
            dest_name=dest_name,
            is_directory=is_directory,
        )
        self.export_tasks.append(task)
        self.logger.debug(f"Added export task: {source_path} -> {dest_name}")

    def remove_export_task(self, dest_name: str) -> bool:
        """Remove an export task by destination name.

        Args:
            dest_name: The destination name of the task to remove.

        Returns:
            True if task was removed, False if not found.
        """
        initial_count = len(self.export_tasks)
        self.export_tasks = [t for t in self.export_tasks if t.dest_name != dest_name]
        removed = len(self.export_tasks) < initial_count

        if removed:
            self.logger.debug(f"Removed export task: {dest_name}")

        return removed

    def clear_export_tasks(self) -> None:
        """Clear all export tasks."""
        self.export_tasks.clear()
        self.logger.debug("Cleared all export tasks")

    def list_devices(self) -> list[USBDevice]:
        """List all currently connected USB storage devices.

        Returns:
            List of connected USB storage devices.

        Example:
            ```python
            devices = manager.list_devices()
            for device in devices:
                print(
                    f"Found: {device.vendor} {device.model} at {device.mount_point}"
                )
            ```
        """
        return self._backend.list_devices()

    async def export(
        self,
        device: USBDevice,
        *,
        tasks: list[USBExportTask] | None = None,
    ) -> dict[str, bool]:
        """Export files/directories to a USB device.

        Args:
            device: Target USB device.
            tasks: List of export tasks. If None, uses self.export_tasks.

        Returns:
            Dictionary mapping dest_name to success status.

        Example:
            ```python
            devices = manager.list_devices()
            if devices:
                results = await manager.export(devices[0])
                for dest, success in results.items():
                    if success:
                        print(f"Exported {dest}")
                    else:
                        print(f"Failed to export {dest}")
            ```
        """
        tasks_to_export = tasks or self.export_tasks
        if not tasks_to_export:
            self.logger.warning("No export tasks defined")
            return {}

        results: dict[str, bool] = {}
        usb_root = pathlib.Path(device.mount_point)

        self.logger.info(f"Starting export of {len(tasks_to_export)} tasks to {device.mount_point}")

        for task in tasks_to_export:
            try:
                dest_path = usb_root / task.dest_name

                # Check if source exists
                if not task.source.exists():
                    self.logger.warning(f"Source does not exist: {task.source}")
                    results[task.dest_name] = False
                    continue

                # Create parent directories
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file or directory
                if task.is_directory:
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(task.source, dest_path)
                    self.logger.info(f"Exported directory: {task.source} -> {dest_path}")
                else:
                    shutil.copy2(task.source, dest_path)
                    self.logger.info(f"Exported file: {task.source} -> {dest_path}")

                results[task.dest_name] = True

            except Exception as e:
                self.logger.error(f"Failed to export {task.dest_name}: {e}", exc_info=True)
                results[task.dest_name] = False

        success_count = sum(1 for success in results.values() if success)
        self.logger.info(f"Export completed: {success_count}/{len(tasks_to_export)} successful")

        return results

    async def start(self) -> None:
        """Start monitoring for USB device connections.

        Will automatically detect when USB devices are connected.

        Example:
            ```python
            manager = USBManager()
            manager.add_export_task(
                "/data/logs", "logs", is_directory=True
            )
            await manager.start()
            # Will monitor for USB connections
            ```
        """
        if self._running:
            self.logger.warning("USB monitor already running")
            return

        self._running = True
        await self._backend.start_monitoring(self._handle_device_event)
        self.logger.info("Started USB device monitoring")

    async def stop(self) -> None:
        """Stop monitoring for USB device connections."""
        if not self._running:
            return

        self._running = False
        await self._backend.stop_monitoring()
        self.logger.info("Stopped USB device monitoring")

    def _handle_device_event(self, action: str, device: t.Any) -> None:
        """Handle USB device events.

        Args:
            action: Event action (add, remove, change).
            device: The device that triggered the event.
        """
        if action != "add":
            return

        # For Linux, check device type
        if hasattr(device, "device_type"):
            if device.device_type != "partition":
                return
            if "usb" not in device.device_path.lower():
                return

        self.logger.info("USB device connected")
