from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.config import Config
    from audex.lib.database.sqlite import SQLite


def make_sqlite(config: Config) -> SQLite:
    from audex.lib.database.sqlite import SQLite
    from audex.lib.repos.tables import TABLES

    return SQLite(
        uri=config.infrastructure.sqlite.uri,
        tables=list(TABLES),
        echo=config.infrastructure.sqlite.echo,
        pool_size=config.infrastructure.sqlite.pool_size,
        max_overflow=config.infrastructure.sqlite.max_overflow,
        pool_recycle=config.infrastructure.sqlite.pool_recycle,
        pool_timeout=config.infrastructure.sqlite.pool_timeout,
        pool_pre_ping=config.infrastructure.sqlite.pool_pre_ping,
    )
