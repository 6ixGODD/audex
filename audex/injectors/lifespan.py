from __future__ import annotations

from audex.lifespan import LifeSpan


def lifespan(*args: object) -> LifeSpan:
    return LifeSpan(*args)
