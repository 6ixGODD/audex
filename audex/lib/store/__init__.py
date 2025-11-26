from __future__ import annotations

import abc
import builtins
import typing as t

from audex import __title__
from audex.helper.mixin import LoggingMixin


class KeyBuilder:
    """Utility class for building store keys with a consistent format.

    Attributes:
        split_char: Character used to split parts of the key.
        prefix: Prefix to prepend to all keys.
    """

    __slots__ = ("prefix", "split_char")

    def __init__(self, split_char: str = "/", prefix: str = __title__) -> None:
        self.split_char = split_char
        self.prefix = prefix

    def build(self, *parts: str) -> str:
        """Build a store key by joining the prefix and parts.

        Args:
            *parts: Parts to include in the key.

        Returns:
            The constructed store key.
        """
        return self.split_char.join((self.prefix, *parts))

    def validate(self, key: str) -> bool:
        """Validate if a given key starts with the defined prefix.

        Args:
            key: The store key to validate.

        Returns:
            True if the key starts with the prefix, False otherwise.
        """
        return key.startswith(self.prefix + self.split_char)


class Store(LoggingMixin, abc.ABC):
    """Abstract base class for storage operations.

    This class defines the interface for storage backends, providing
    methods for uploading, downloading, deleting, and managing stored
    objects.
    """

    @property
    @abc.abstractmethod
    def key_builder(self) -> KeyBuilder:
        """Get a KeyBuilder instance for constructing store keys.

        Returns:
            An instance of KeyBuilder.
        """

    @abc.abstractmethod
    async def upload(
        self,
        data: bytes | t.IO[bytes],
        key: str,
        metadata: t.Mapping[str, t.Any] | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Upload data to storage.

        Args:
            data: The data to upload, either as bytes or a file-like object.
            key: The unique identifier for the stored object.
            metadata: Optional metadata to associate with the object.
            **kwargs: Additional storage-specific parameters.

        Returns:
            The key of the uploaded object.

        Raises:
            Exception: If the upload fails.
        """

    @abc.abstractmethod
    async def upload_multipart(
        self,
        parts: t.AsyncIterable[bytes],
        key: str,
        metadata: t.Mapping[str, t.Any] | None = None,
        **kwargs: t.Any,
    ) -> str:
        """Upload data in multiple parts.

        Args:
            parts: An async iterable of byte chunks to upload.
            key: The unique identifier for the stored object.
            metadata: Optional metadata to associate with the object.
            **kwargs: Additional storage-specific parameters.

        Returns:
            The key of the uploaded object.

        Raises:
            Exception: If the multipart upload fails.
        """

    @abc.abstractmethod
    async def get_metadata(self, key: str) -> builtins.dict[str, t.Any]:
        """Retrieve metadata for a stored object.

        Args:
            key: The unique identifier of the object.

        Returns:
            A dictionary containing the object's metadata.

        Raises:
            Exception: If the object doesn't exist or metadata retrieval fails.
        """

    @t.overload
    async def download(
        self,
        key: str,
        *,
        stream: t.Literal[False] = False,
        chunk_size: int = 8192,
        **kwargs: t.Any,
    ) -> bytes: ...
    @t.overload
    async def download(
        self,
        key: str,
        *,
        stream: t.Literal[True],
        chunk_size: int = 8192,
        **kwargs: t.Any,
    ) -> bytes: ...
    @abc.abstractmethod
    async def download(
        self,
        key: str,
        *,
        stream: bool = False,
        chunk_size: int = 8192,
        **kwargs: t.Any,
    ) -> bytes | t.AsyncIterable[bytes]:
        """Download data from storage.

        Args:
            key: The unique identifier of the object to download.
            stream: If True, return an async iterable of chunks; otherwise return all bytes.
            chunk_size: Size of each chunk when streaming (in bytes).
            **kwargs: Additional storage-specific parameters.

        Returns:
            The object's data as bytes, or an async iterable of byte chunks if streaming.

        Raises:
            Exception: If the download fails or object doesn't exist.
        """

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        """Delete an object from storage.

        Args:
            key: The unique identifier of the object to delete.

        Raises:
            Exception: If the deletion fails.
        """

    @abc.abstractmethod
    def list(
        self,
        prefix: str = "",
        page_size: int = 10,
        **kwargs: t.Any,
    ) -> t.AsyncIterable[builtins.list[str]]:
        """List objects in storage with the given prefix.

        Args:
            prefix: Optional prefix to filter objects.
            page_size: Number of object keys to return per iteration.
            **kwargs: Additional storage-specific parameters.

        Yields:
            Lists of object keys matching the prefix.

        Raises:
            Exception: If listing fails.
        """

    @abc.abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if an object exists in storage.

        Args:
            key: The unique identifier of the object.

        Returns:
            True if the object exists, False otherwise.

        Raises:
            Exception: If the existence check fails.
        """

    @abc.abstractmethod
    async def clear(self, prefix: str = "") -> None:
        """Delete all objects with the given prefix.

        Args:
            prefix: Optional prefix to filter objects for deletion.

        Raises:
            Exception: If the clear operation fails.
        """

    @abc.abstractmethod
    async def copy(self, source_key: str, dest_key: str, **kwargs: t.Any) -> str:
        """Copy an object to a new location.

        Args:
            source_key: The unique identifier of the source object.
            dest_key: The unique identifier for the destination object.
            **kwargs: Additional storage-specific parameters.

        Returns:
            The key of the copied object.

        Raises:
            Exception: If the copy operation fails.
        """
