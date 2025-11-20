from __future__ import annotations

from audex.helper.settings import Settings


class Config(Settings):
    pass


def getconfig() -> Config:
    return Config()
