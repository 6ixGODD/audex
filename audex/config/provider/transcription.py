from __future__ import annotations

import typing as t

from pydantic import Field

from audex.config.helper.provider.dashscope import DashscopeCredentialConfig
from audex.helper.settings import BaseModel


class DashscopeTranscriptionConfig(BaseModel):
    credential: DashscopeCredentialConfig = Field(
        default_factory=DashscopeCredentialConfig,
        description="Credentials for Dashscope API access.",
    )

    model: str = Field(
        default="paraformer-realtime-v2",
        description="Dashscope transcription model to use.",
    )

    user_agent: str | None = Field(
        default=None,
        description="Custom User-Agent header for API requests.",
    )

    workspace: str | None = Field(
        default=None,
        description="Workspace identifier for Dashscope service.",
    )

    max_connections: int = Field(
        default=10,
        description="Maximum concurrent connections to Dashscope API.",
    )

    drain_timeout: float = Field(
        default=5.0,
        description="Timeout in seconds to drain connections on shutdown.",
    )


class TranscriptionConfig(BaseModel):
    provider: t.Literal["dashscope"] = Field(
        default="dashscope",
        description="The transcription service provider.",
    )

    dashscope: DashscopeTranscriptionConfig = Field(
        default_factory=DashscopeTranscriptionConfig,
        description="Configuration for Dashscope transcription service.",
    )
