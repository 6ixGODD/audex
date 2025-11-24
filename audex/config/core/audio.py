from __future__ import annotations

from pydantic import Field

from audex.helper.settings import BaseModel


class AudioConfig(BaseModel):
    sample_rate: int = Field(
        default=16000,
        description="The sample rate of the audio in Hz.",
    )
