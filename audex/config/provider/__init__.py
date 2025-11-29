from __future__ import annotations

from audex.config.provider.transcription import TranscriptionConfig
from audex.config.provider.vpr import VPRConfig
from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field


class ProviderConfig(BaseModel):
    transcription: TranscriptionConfig = Field(
        default_factory=TranscriptionConfig,
        description="Transcription provider configuration",
    )

    vpr: VPRConfig = Field(
        default_factory=VPRConfig,
        description="VPR provider configuration",
    )
