from __future__ import annotations

import typing as t

from pydantic import Field

from audex.config.helper.client.websocket import WebsocketClientConfig
from audex.config.helper.provider.dashscope import DashscopeCredentialConfig
from audex.helper.settings import BaseModel


class DashscopeTranscriptionSessionConfig(BaseModel):
    fmt: t.Literal["pcm", "wav", "mp3", "opus", "speex", "aac", "amr"] = Field(
        default="pcm",
        description="Audio format for transcription session.",
    )

    sample_rate: t.Literal[8000, 16000, 22050, 24000, 44100, 48000] = Field(
        default=16000,
        description="Sample rate of the audio in Hz.",
    )

    silence_duration_ms: int | None = Field(
        default=None,
        description="Duration of silence in milliseconds to consider as end of speech.",
    )

    vocabulary_id: str | None = Field(
        default=None,
        description="Custom vocabulary ID for transcription.",
    )

    disfluency_removal_enabled: bool | None = Field(
        default=None,
        description="Enable disfluency removal in transcription.",
    )

    lang_hints: list[t.Literal["zh", "en", "ja", "yue", "ko", "de", "fr", "ru"]] | None = Field(
        default=None,
        description="Language hints for transcription.",
    )

    semantic_punctuation: bool | None = Field(
        default=None,
        description="Enable semantic punctuation in transcription.",
    )

    multi_thres_mode: bool | None = Field(
        default=None,
        description="Enable multi-threshold mode for transcription.",
    )

    punctuation_pred: bool | None = Field(
        default=None,
        description="Enable punctuation prediction in transcription.",
    )

    heartbeat: bool | None = Field(
        default=None,
        description="Enable heartbeat messages during transcription.",
    )

    itn: bool | None = Field(
        default=None,
        description="Enable inverse text normalization in transcription.",
    )

    resources: list[str] | None = Field(
        default=None,
        description="List of resource identifiers for transcription.",
    )


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

    websocket: WebsocketClientConfig = Field(
        default_factory=WebsocketClientConfig,
        description="WebSocket client configuration for Dashscope.",
    )

    session: DashscopeTranscriptionSessionConfig = Field(
        default_factory=DashscopeTranscriptionSessionConfig,
        description="Session configuration for Dashscope transcription.",
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
