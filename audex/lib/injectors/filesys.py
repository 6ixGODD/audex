from __future__ import annotations

from audex.config import Config
from audex.lib.filesys import FileSystemManager


def make_filesys(config: Config) -> FileSystemManager:
    log_paths = [
        target.logname
        for target in config.core.logging.targets
        if target.logname not in ("stderr", "stdout")
    ]
    return FileSystemManager(
        store_path=config.infrastructure.store.base_url,
        log_paths=log_paths,
    )
