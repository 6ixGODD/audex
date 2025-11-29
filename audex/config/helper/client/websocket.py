from __future__ import annotations

from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field


class WebsocketClientConfig(BaseModel):
    max_connections: int = Field(
        default=10,
        description="Maximum concurrent connections to Dashscope API.",
    )

    idle_timeout: int = Field(
        default=60,
        description="Idle timeout in seconds for websocket connections.",
    )

    drain_timeout: float = Field(
        default=5.0,
        description="Timeout in seconds to drain connections on shutdown.",
    )
