from __future__ import annotations

import asyncio
import contextlib
import os
import pathlib
import shutil
import typing as t

import pyudev  # type: ignore

from audex.helper.mixin import LoggingMixin


class USBDevice(t.NamedTuple):
    """Represents a USB storage device.

    Attributes:
        device_node: Device node path (e.g., /dev/sdb1).
        mount_point: Where the device is mounted (e.g., /media/usb).
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


class USBManager(LoggingMixin):
    """USB storage device manager for file export.

    This manager monitors USB device connections and provides functionality
    to export files and directories to connected USB drives. It uses pyudev
    to detect device connections and mount points.

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
            await manager.export_to_device(devices[0])

        # Stop monitoring
        await manager.stop()
        ```
    """

    __logtag__ = "audex.lib.usb.manager"

    def __init__(self) -> None:
        super().__init__()
        self.export_tasks: list[USBExportTask] = []

        self._context = pyudev.Context()
        self._monitor: pyudev.Monitor | None = None  # type: ignore
        self._monitor_task: asyncio.Task[None] | None = None
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
        devices: list[USBDevice] = []

        # Enumerate USB storage devices
        for device in self._context.list_devices(subsystem="block", DEVTYPE="partition"):
            # Check if it's a USB device
            if "usb" not in device.device_path.lower():
                continue

            # Try to get mount point
            mount_point = self._get_mount_point(device.device_node)
            if not mount_point:
                continue

            # Get device properties
            id_vendor = device.get("ID_VENDOR", "Unknown")
            id_model = device.get("ID_MODEL", "Unknown")
            id_fs_type = device.get("ID_FS_TYPE")
            id_fs_label = device.get("ID_FS_LABEL")

            # Try to get size
            size_bytes = None
            size_file = pathlib.Path(f"/sys/class/block/{device.sys_name}/size")
            if size_file.exists():
                try:
                    # Size is in 512-byte sectors
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
        """Get the mount point for a device node.

        Args:
            device_node: Device node path (e.g., /dev/sdb1).

        Returns:
            Mount point path, or None if not mounted.
        """
        try:
            with pathlib.Path("/proc/mounts").open("r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == device_node:
                        return parts[1]
        except OSError as e:
            self.logger.warning(f"Failed to read /proc/mounts: {e}")

        return None

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
                results = await manager.export_to_device(devices[0])
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

        If auto_export is enabled, will automatically export when a USB
        device is connected.

        Example:
            ```python
            manager = USBManager(auto_export=True)
            manager.add_export_task(
                "/data/logs", "logs", is_directory=True
            )
            await manager.start()
            # Will automatically export when USB is connected
            ```
        """
        if self._running:
            self.logger.warning("USB monitor already running")
            return

        self._monitor = pyudev.Monitor.from_netlink(self._context)
        self._monitor.filter_by(subsystem="block")
        self._running = True

        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("Started USB device monitoring")

    async def stop(self) -> None:
        """Stop monitoring for USB device connections."""
        if not self._running:
            return

        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task
            self._monitor_task = None

        self._monitor = None
        self.logger.info("Stopped USB device monitoring")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop for USB events."""
        if self._monitor is None:
            return

        observer = pyudev.MonitorObserver(self._monitor, self._handle_device_event)
        observer.start()

        try:
            while self._running:
                await asyncio.sleep(1)
        finally:
            observer.stop()

    def _handle_device_event(self, action: str, device: pyudev.Device) -> None:
        """Handle USB device events.

        Args:
            action: Event action (add, remove, change).
            device: The device that triggered the event.
        """
        if action != "add":
            return

        # Check if it's a USB storage device
        if device.device_type != "partition":
            return

        if "usb" not in device.device_path.lower():
            return

        self.logger.info(f"USB device connected: {device.device_node}")
