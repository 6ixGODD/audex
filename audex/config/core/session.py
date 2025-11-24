from __future__ import annotations

from pydantic import Field

from audex.helper.settings import BaseModel


class SessionConfig(BaseModel):
    ttl_hours: float = Field(
        default=24 * 7,
        description="Time to live for a session in hours.",
    )
