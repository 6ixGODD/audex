from __future__ import annotations

from dataclasses import dataclass


class FileSystemError(Exception):
    """Base exception for file system operations."""


class DirectoryNotFoundError(FileSystemError):
    """Directory not found."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Directory not found: {path}")


class DirectoryNotWritableError(FileSystemError):
    """Directory is not writable."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Directory is not writable: {path}")


class ClearOperationError(FileSystemError):
    """Error occurred during clear operation."""

    def __init__(self, operation: str, path: str, original_error: Exception):
        self.operation = operation
        self.path = path
        self.original_error = original_error
        super().__init__(f"{operation} failed for {path}: {original_error}")


@dataclass
class FailedItem:
    """Information about a failed operation on a single item."""

    path: str
    error: Exception


class PartialClearError(FileSystemError):
    """Some items failed to clear, but operation partially succeeded."""

    def __init__(
        self,
        operation: str,
        succeeded_count: int,
        failed_items: list[FailedItem],
        space_freed: int,
    ):
        self.operation = operation
        self.succeeded_count = succeeded_count
        self.failed_items = failed_items
        self.space_freed = space_freed
        self.failed_count = len(failed_items)

        super().__init__(f"{operation}: {succeeded_count} succeeded, {self.failed_count} failed")


class DiskSpaceError(FileSystemError):
    """Insufficient disk space."""

    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient disk space: required {required} bytes, available {available} bytes"
        )
