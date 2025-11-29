from __future__ import annotations

import typing as t

from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field


class HttpClientConfig(BaseModel):
    proxy: str | None = Field(
        default=None,
        description="Proxy URL to route HTTP requests through. Example: 'http://localhost:8080'",
    )

    timeout: float = Field(
        default=10.0,
        description="Timeout in seconds for HTTP requests.",
    )

    default_headers: dict[str, str] | None = Field(
        default=None,
        description="Default headers to include in every HTTP request.",
    )

    default_params: dict[str, t.Any] | None = Field(
        default=None,
        description="Default query parameters to include in every HTTP request.",
    )
