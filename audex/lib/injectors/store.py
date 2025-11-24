from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.config.helper.store import StoreConfig
    from audex.lib.store import Store


def build_store(config: StoreConfig) -> Store:
    from audex.lib.store.localfile import LocalFileStore

    return LocalFileStore(config.base_url)
