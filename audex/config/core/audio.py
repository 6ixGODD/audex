from __future__ import annotations

from pydantic import Field

from audex.helper.settings import BaseModel


class AudioConfig(BaseModel):
    sample_rate: str = Field(
        default=16000,
        description="The sample rate of the audio in Hz.",
    )

    vpr_sample_rate: int = Field(
        default=16000,
        description="The sample rate for voice print recognition in Hz.",
    )

    vpr_text_content: str = Field(
        default="请朗读: 您好，请问您今天需要什么帮助？",
        min_length=10,
        max_length=100,
        description="The text content used for voice print recognition.",
    )

    vpr_threshold: float = Field(
        default=0.6,
        gt=0.0,
        lt=1.0,
        description="The threshold for voice print recognition similarity.",
    )

    key_prefix: str = Field(
        default="audex",
        min_length=1,
        max_length=50,
        description="The prefix for storing audio files in cloud storage.",
    )

    segment_buffer: int = Field(
        default=200,
        gt=0,
        lt=5000,
        description="The buffer time in milliseconds for audio segmentation.",
    )
