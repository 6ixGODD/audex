from __future__ import annotations

from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field


class SessionConfig(BaseModel):
    ttl_hours: float = Field(
        default=24 * 7,
        description="Time to live for a session in hours.",
    )
