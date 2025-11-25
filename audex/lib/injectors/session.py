from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.config import Config
    from audex.lib.session import SessionManager


def make_session_manager(config: Config) -> SessionManager:
    import datetime

    from audex.lib.session import SessionManager

    return SessionManager(
        app_name=config.core.app.app_name,
        ttl=datetime.timedelta(hours=config.core.session.ttl_hours),
    )
