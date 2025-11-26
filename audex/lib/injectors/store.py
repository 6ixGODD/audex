from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.config import Config
    from audex.lib.store import Store


def make_store(config: Config) -> Store:
    from audex.lib.store.localfile import LocalFileStore

    return LocalFileStore(config.infrastructure.store.base_url)
