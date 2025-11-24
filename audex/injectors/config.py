from __future__ import annotations

from audex.config import Config
from audex.config import build_config
from audex.config import getconfig


def config() -> Config:
    try:
        return getconfig()
    except RuntimeError:
        return build_config()
