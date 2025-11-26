from __future__ import annotations

import builtins
import json
import pathlib
import typing as t

import aiofiles
import aiofiles.os

from audex.lib.store import KeyBuilder
from audex.lib.store import Store


class LocalFileStore(Store):
    """File-based storage implementation using local filesystem.

    Args:
        base_path: Base directory path for storing files
    """

    __logtag__ = "audex.lib.store.localfile"

    METADATA_SUFFIX: t.ClassVar[str] = ".metadata.json"
    DEFAULT_CHUNK_SIZE: t.ClassVar[int] = 8192

    def __init__(self, base_path: str | pathlib.Path):
        super().__init__()
        self.base_path = pathlib.Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._key_builder = KeyBuilder(split_char="/", prefix="")

    @property
    def key_builder(self) -> KeyBuilder:
        return self._key_builder

    def fullpath(self, key: str) -> pathlib.Path:
        """Get the full file path for a given key.

        Args:
            key: File key

        Returns:
            Full resolved file path

        Raises:
            ValueError: If the key attempts to escape the base_path
        """
        # Remove leading slashes to prevent path injection
        key = key.lstrip("/")
        full_path = (self.base_path / key).resolve()

        # Security check: ensure path is within base_path
        if not str(full_path).startswith(str(self.base_path)):
            raise ValueError(f"Invalid key: {key}")

        return full_path

    def metadata_path(self, key: str) -> pathlib.Path:
        """Get the metadata file path for a given key.

        Args:
            key: File key

        Returns:
            Metadata file path
        """
        file_path = self.fullpath(key)
        return file_path.parent / (file_path.name + self.METADATA_SUFFIX)

    async def upload(
        self,
        data: bytes | t.IO[bytes],
        key: str,
        metadata: t.Mapping[str, t.Any] | None = None,
        **_kwargs: t.Any,
    ) -> str:
        """Upload a file.

        Args:
            data: File data (bytes or file-like object)
            key: File key
            metadata: Additional metadata
            **_kwargs: Additional arguments (unused)

        Returns:
            File key

        Raises:
            ValueError: If the key is invalid
        """
        file_path = self.fullpath(key)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        async with aiofiles.open(file_path, "wb") as f:
            if isinstance(data, bytes):
                await f.write(data)
            else:
                # Handle file object
                while True:
                    chunk = data.read(self.DEFAULT_CHUNK_SIZE)
                    if not chunk:
                        break
                    await f.write(chunk)

        # Write metadata if provided
        if metadata:
            metadata_file = self.metadata_path(key)
            async with aiofiles.open(metadata_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))

        return key

    async def upload_multipart(
        self,
        parts: t.AsyncIterable[bytes],
        key: str,
        metadata: t.Mapping[str, t.Any] | None = None,
        **_kwargs: t.Any,
    ) -> str:
        """Upload a file from multiple parts.

        Args:
            parts: Async iterable of file data parts
            key: File key
            metadata: Additional metadata
            **_kwargs: Additional arguments (unused)

        Returns:
            File key

        Raises:
            ValueError: If the key is invalid
        """
        file_path = self.fullpath(key)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file parts
        async with aiofiles.open(file_path, "wb") as f:
            async for part in parts:
                await f.write(part)

        # Write metadata if provided
        if metadata:
            metadata_file = self.metadata_path(key)
            async with aiofiles.open(metadata_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))

        return key

    async def get_metadata(self, key: str) -> builtins.dict[str, t.Any]:
        """Get metadata for a file.

        Args:
            key: File key

        Returns:
            Metadata dictionary (empty if no metadata exists)

        Raises:
            FileNotFoundError: If the file does not exist
        """
        file_path = self.fullpath(key)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        if not file_path.is_file():
            raise IsADirectoryError(f"Path is not a file: {key}")

        metadata_file = self.metadata_path(key)

        if not metadata_file.exists():
            return {}

        async with aiofiles.open(metadata_file, encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)  # type: ignore

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
    async def download(
        self,
        key: str,
        *,
        stream: bool = False,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        **_kwargs: t.Any,
    ) -> bytes | t.AsyncIterable[bytes]:
        """Download a file.

        Args:
            key: File key
            stream: Whether to return as a stream
            chunk_size: Size of each chunk in bytes (used if stream is True)
            **_kwargs: Additional arguments (unused)

        Returns:
            File data (bytes or async iterator)

        Raises:
            FileNotFoundError: If the file does not exist
            IsADirectoryError: If the path is a directory
        """
        file_path = self.fullpath(key)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        if not file_path.is_file():
            raise IsADirectoryError(f"Path is not a file: {key}")

        if stream:
            return self.stream_file(file_path, chunk_size)
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def stream_file(
        self,
        file_path: pathlib.Path,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> t.AsyncIterable[bytes]:
        """Stream a file in chunks.

        Args:
            file_path: Path to the file
            chunk_size: Size of each chunk in bytes

        Yields:
            File data chunks
        """
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    async def delete(self, key: str) -> None:
        """Delete a file and its metadata.

        Args:
            key: File key

        Raises:
            IsADirectoryError: If the path is a directory
        """
        file_path = self.fullpath(key)

        if file_path.exists():
            if file_path.is_file():
                await aiofiles.os.remove(file_path)

                # Delete metadata file if exists
                metadata_file = self.metadata_path(key)
                if metadata_file.exists():
                    await aiofiles.os.remove(metadata_file)
            else:
                raise IsADirectoryError(f"Path is not a file: {key}")

    async def list(
        self,
        prefix: str = "",
        page_size: int = 10,
        **_kwargs: t.Any,
    ) -> t.AsyncIterable[builtins.list[str]]:
        """List files with a given prefix.

        Args:
            prefix: Key prefix to filter files
            page_size: Number of items per page
            **_kwargs: Additional arguments (unused)

        Returns:
            List of file keys matching the prefix (excludes metadata files)
        """
        prefix = prefix.lstrip("/")
        search_path = self.base_path / prefix if prefix else self.base_path

        if not search_path.exists():
            yield []
        else:
            current_page: builtins.list[str] = []
            for item in search_path.rglob("*"):
                if item.is_file() and not item.name.endswith(self.METADATA_SUFFIX):
                    relative_path = item.relative_to(self.base_path)
                    current_page.append(str(relative_path))

                    if len(current_page) >= page_size:
                        yield current_page
                        current_page = []

            if current_page:  # Yield any remaining items
                yield current_page

    async def exists(self, key: str) -> bool:
        """Check if a file exists.

        Args:
            key: File key

        Returns:
            True if the file exists, False otherwise
        """
        file_path = self.fullpath(key)
        return file_path.exists() and file_path.is_file()

    async def clear(self, prefix: str = "") -> None:
        """Clear files with a given prefix.

        Args:
            prefix: Key prefix to filter files
        """
        prefix = prefix.lstrip("/")
        search_path = self.base_path / prefix if prefix else self.base_path

        if not search_path.exists():
            return

        # If search_path is a file, delete it directly
        if search_path.is_file():
            await aiofiles.os.remove(search_path)
            # Delete metadata file if exists
            if not search_path.name.endswith(self.METADATA_SUFFIX):
                metadata_file = search_path.parent / (search_path.name + self.METADATA_SUFFIX)
                if metadata_file.exists():
                    await aiofiles.os.remove(metadata_file)
            return

        # Recursively traverse directory and delete files
        for item in search_path.rglob("*"):
            if item.is_file():
                await aiofiles.os.remove(item)

    async def copy(self, source_key: str, dest_key: str, **_kwargs: t.Any) -> str:
        """Copy a file and its metadata.

        Args:
            source_key: Source file key
            dest_key: Destination file key
            **_kwargs: Additional arguments (unused)

        Returns:
            Destination file key

        Raises:
            FileNotFoundError: If the source file does not exist
            IsADirectoryError: If the source path is a directory
        """
        source_path = self.fullpath(source_key)
        dest_path = self.fullpath(dest_key)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_key}")

        if not source_path.is_file():
            raise IsADirectoryError(f"Source path is not a file: {source_key}")

        # Ensure parent directory of destination exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        async with (
            aiofiles.open(source_path, "rb") as src_file,
            aiofiles.open(dest_path, "wb") as dest_file,
        ):
            while True:
                chunk = await src_file.read(self.DEFAULT_CHUNK_SIZE)
                if not chunk:
                    break
                await dest_file.write(chunk)

        # Copy metadata file if exists
        source_metadata = self.metadata_path(source_key)
        if source_metadata.exists():
            dest_metadata = self.metadata_path(dest_key)
            async with (
                aiofiles.open(source_metadata, "rb") as src_meta,
                aiofiles.open(dest_metadata, "wb") as dest_meta,
            ):
                while True:
                    chunk = await src_meta.read(self.DEFAULT_CHUNK_SIZE)
                    if not chunk:
                        break
                    await dest_meta.write(chunk)

        return dest_key

    def __repr__(self) -> str:
        return f"FILE STORE <{self.__class__.__name__}(base_path={self.base_path})>"
