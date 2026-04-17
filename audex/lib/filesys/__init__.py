from __future__ import annotations

import os
from dataclasses import dataclass
import pathlib
import platform
import shutil

import aiofiles
import aiofiles.os

from audex.lib.filesys.exceptions import ClearOperationError
from audex.lib.filesys.exceptions import DirectoryNotFoundError
from audex.lib.filesys.exceptions import DirectoryNotWritableError
from audex.lib.filesys.exceptions import FailedItem
from audex.lib.filesys.exceptions import FileSystemError
from audex.lib.filesys.exceptions import PartialClearError


@dataclass
class DiskUsage:
    """Disk usage statistics."""

    total: int  # Total bytes
    used: int  # Used bytes
    free: int  # Free bytes
    percent: float  # Usage percentage


@dataclass
class DirectoryInfo:
    """Directory information."""

    path: pathlib.Path
    exists: bool
    size: int  # Total size in bytes
    file_count: int  # Number of files
    is_writable: bool


@dataclass
class ClearResult:
    """Result of a successful clear operation."""

    files_cleared: int  # Number of files cleared
    space_freed: int  # Bytes freed


class FileSystemManager:
    """File system manager for managing store and logs directories."""

    __logtag__ = "audex.lib.filesys"

    def __init__(self, store_path: str | pathlib.Path, log_paths: list[str | os.PathLike[str]]):
        """Initialize file system manager.

        Args:
            store_path: Path to the store directory
            log_paths: List of log file paths

        Raises:
            DirectoryNotWritableError: If store_path is not writable
        """
        self.store_path = pathlib.Path(store_path).resolve()
        self.log_paths = [pathlib.Path(p).resolve() for p in log_paths]

        # Ensure store path exists
        try:
            self.store_path.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise DirectoryNotWritableError(str(self.store_path)) from e

    def get_store_path(self) -> pathlib.Path:
        """Get the store directory path.

        Returns:
            Absolute path to the store directory
        """
        return self.store_path

    async def get_directory_info(self, path: pathlib.Path) -> DirectoryInfo:
        """Get information about a directory.

        Args:
            path: Directory path

        Returns:
            Directory information

        Raises:
            FileSystemError: If unable to read directory information
        """
        exists = path.exists()
        if not exists:
            return DirectoryInfo(
                path=path,
                exists=False,
                size=0,
                file_count=0,
                is_writable=False,
            )

        # Calculate total size and file count
        total_size = 0
        file_count = 0

        try:
            for item in path.rglob("*"):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                        file_count += 1
                    except (OSError, PermissionError):
                        # Skip files we can't read
                        pass
        except (OSError, PermissionError) as e:
            raise FileSystemError(f"Failed to read directory: {path}") from e

        # Check if writable
        is_writable = True
        try:
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
        except (OSError, PermissionError):
            is_writable = False

        return DirectoryInfo(
            path=path,
            exists=True,
            size=total_size,
            file_count=file_count,
            is_writable=is_writable,
        )

    async def get_logs_info(self) -> DirectoryInfo:
        """Get information about all log files.

        Returns:
            Combined log files information

        Raises:
            FileSystemError: If unable to read log information
        """
        total_size = 0
        file_count = 0
        exists = False

        for log_path in self.log_paths:
            if log_path.exists():
                exists = True
                try:
                    if log_path.is_file():
                        total_size += log_path.stat().st_size
                        file_count += 1
                    elif log_path.is_dir():
                        # Count all log files in directory
                        for log_file in log_path.rglob("*.log"):
                            try:
                                total_size += log_file.stat().st_size
                                file_count += 1
                            except (OSError, PermissionError):
                                pass
                        for jsonl_file in log_path.rglob("*.jsonl"):
                            try:
                                total_size += jsonl_file.stat().st_size
                                file_count += 1
                            except (OSError, PermissionError):
                                pass
                except (OSError, PermissionError) as e:
                    raise FileSystemError(f"Failed to read log path: {log_path}") from e

        # Determine common path
        if self.log_paths:
            common_path = (
                self.log_paths[0] if len(self.log_paths) == 1 else pathlib.Path("多个路径")
            )
        else:
            common_path = pathlib.Path("无日志路径")

        return DirectoryInfo(
            path=common_path,
            exists=exists,
            size=total_size,
            file_count=file_count,
            is_writable=True,  # Assume writable if we can read
        )

    def get_disk_usage(self, path: pathlib.Path | None = None) -> DiskUsage:
        """Get disk usage statistics for the partition containing the path.

        Args:
            path: Path to check (defaults to store_path)

        Returns:
            Disk usage statistics

        Raises:
            FileSystemError: If unable to get disk usage
        """
        if path is None:
            path = self.store_path

        # Ensure path exists
        if not path.exists():
            path = path.parent

        try:
            usage = shutil.disk_usage(path)

            return DiskUsage(
                total=usage.total,
                used=usage.used,
                free=usage.free,
                percent=round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0.0,
            )
        except (OSError, PermissionError) as e:
            raise FileSystemError(f"Failed to get disk usage for: {path}") from e

    def get_mount_point(self, path: pathlib.Path | None = None) -> str:
        """Get the mount point for a given path.

        Args:
            path: Path to check (defaults to store_path)

        Returns:
            Mount point path as string

        Raises:
            FileSystemError: If unable to determine mount point
        """
        if path is None:
            path = self.store_path

        try:
            system = platform.system()

            if system == "Windows":
                # Windows: return drive letter
                return str(pathlib.Path(path).drive)
            # Linux/Mac: find mount point
            path = path.resolve()
            while not path.is_mount() and path.parent != path:
                path = path.parent
            return str(path)
        except (OSError, PermissionError) as e:
            raise FileSystemError(f"Failed to get mount point for: {path}") from e

    async def clear_store(self) -> ClearResult:
        """Clear all files in the store directory.

        Returns:
            ClearResult with operation statistics

        Raises:
            DirectoryNotFoundError: If store directory doesn't exist
            ClearOperationError: If clear operation fails completely
            PartialClearError: If some files failed to clear
        """
        if not self.store_path.exists():
            raise DirectoryNotFoundError(str(self.store_path))

        # Calculate total size and count before clearing
        total_size = 0
        file_count = 0
        for item in self.store_path.rglob("*"):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                    file_count += 1
                except (OSError, PermissionError):
                    pass

        # Remove all files and subdirectories
        failed_items: list[FailedItem] = []
        succeeded_count = 0
        space_freed = 0

        for item in self.store_path.iterdir():
            try:
                # Track size before deletion
                item_size = 0
                if item.is_file():
                    item_size = item.stat().st_size
                elif item.is_dir():
                    for subitem in item.rglob("*"):
                        if subitem.is_file():
                            try:
                                item_size += subitem.stat().st_size
                            except (OSError, PermissionError):
                                pass

                # Delete
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

                space_freed += item_size
                succeeded_count += 1

            except Exception as e:
                failed_items.append(FailedItem(path=str(item), error=e))

        # Check results
        if failed_items and succeeded_count == 0:
            # Complete failure
            raise ClearOperationError(
                operation="clear_store",
                path=str(self.store_path),
                original_error=failed_items[0].error,
            )

        if failed_items:
            # Partial failure
            raise PartialClearError(
                operation="clear_store",
                succeeded_count=succeeded_count,
                failed_items=failed_items,
                space_freed=space_freed,
            )

        # Complete success
        return ClearResult(
            files_cleared=file_count,
            space_freed=total_size,
        )

    async def clear_logs(self) -> ClearResult:
        """Clear all log files.

        Returns:
            ClearResult with operation statistics

        Raises:
            ClearOperationError: If clear operation fails completely
            PartialClearError: If some log files failed to clear
        """
        cleared_count = 0
        total_size = 0
        failed_items: list[FailedItem] = []

        for log_path in self.log_paths:
            try:
                if log_path.exists() and log_path.is_file():
                    size = log_path.stat().st_size
                    total_size += size
                    # Clear file content instead of deleting
                    async with aiofiles.open(log_path, "w") as f:
                        await f.write("")
                    cleared_count += 1
                elif log_path.exists() and log_path.is_dir():
                    # If it's a directory, clear all log files inside
                    for log_file in log_path.rglob("*.log"):
                        try:
                            size = log_file.stat().st_size
                            total_size += size
                            async with aiofiles.open(log_file, "w") as f:
                                await f.write("")
                            cleared_count += 1
                        except Exception as e:
                            failed_items.append(FailedItem(path=str(log_file), error=e))

                    for jsonl_file in log_path.rglob("*.jsonl"):
                        try:
                            size = jsonl_file.stat().st_size
                            total_size += size
                            async with aiofiles.open(jsonl_file, "w") as f:
                                await f.write("")
                            cleared_count += 1
                        except Exception as e:
                            failed_items.append(FailedItem(path=str(jsonl_file), error=e))

            except Exception as e:
                failed_items.append(FailedItem(path=str(log_path), error=e))

        # Check results
        if failed_items and cleared_count == 0:
            # Complete failure
            raise ClearOperationError(
                operation="clear_logs",
                path="log_paths",
                original_error=failed_items[0].error,
            )

        if failed_items:
            # Partial failure
            raise PartialClearError(
                operation="clear_logs",
                succeeded_count=cleared_count,
                failed_items=failed_items,
                space_freed=total_size,
            )

        # Complete success
        return ClearResult(
            files_cleared=cleared_count,
            space_freed=total_size,
        )

    async def clear_all(self) -> tuple[ClearResult, ClearResult]:
        """Clear both store and logs.

        Returns:
            Tuple of (store_result, logs_result)

        Raises:
            ClearOperationError: If both operations fail completely
            PartialClearError: If some items failed to clear

        Note:
            This method will attempt both operations even if one fails.
            Individual exceptions are collected and re-raised as needed.
        """
        store_result: ClearResult | None = None
        logs_result: ClearResult | None = None
        store_error: Exception | None = None
        logs_error: Exception | None = None

        # Try to clear store
        try:
            store_result = await self.clear_store()
        except Exception as e:
            store_error = e

        # Try to clear logs
        try:
            logs_result = await self.clear_logs()
        except Exception as e:
            logs_error = e

        # If both succeeded, return results
        if store_result is not None and logs_result is not None:
            return store_result, logs_result

        # If both failed completely, raise first error
        if store_result is None and logs_result is None:
            if store_error:
                raise store_error
            if logs_error:
                raise logs_error

        # If one succeeded and one failed, construct partial error
        failed_items: list[FailedItem] = []
        succeeded_count = 0
        space_freed = 0

        if store_result:
            succeeded_count += store_result.files_cleared
            space_freed += store_result.space_freed
        elif store_error:
            if isinstance(store_error, PartialClearError):
                succeeded_count += store_error.succeeded_count
                space_freed += store_error.space_freed
                failed_items.extend(store_error.failed_items)
            else:
                failed_items.append(FailedItem(path=str(self.store_path), error=store_error))

        if logs_result:
            succeeded_count += logs_result.files_cleared
            space_freed += logs_result.space_freed
        elif logs_error:
            if isinstance(logs_error, PartialClearError):
                succeeded_count += logs_error.succeeded_count
                space_freed += logs_error.space_freed
                failed_items.extend(logs_error.failed_items)
            else:
                failed_items.append(FailedItem(path="logs", error=logs_error))

        raise PartialClearError(
            operation="clear_all",
            succeeded_count=succeeded_count,
            failed_items=failed_items,
            space_freed=space_freed,
        )

    @staticmethod
    def format_bytes(size: int) -> str:
        """Format bytes to human-readable string.

        Args:
            size: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 GB")
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
