from __future__ import annotations

import typing as t

from pydantic import Field

from audex.helper.settings import BaseModel


class RecorderConfig(BaseModel):
    format: t.Literal["float32", "int32", "int16", "int8", "uint8"] = Field(
        default="int16",
        description="Audio sample format.",
    )

    channels: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Number of audio channels.",
    )

    rate: int = Field(
        default=16000,
        ge=8000,
        le=192000,
        description="Sampling rate in Hz.",
    )

    chunk: int = Field(
        default=1024,
        ge=256,
        le=8192,
        description="Number of frames per buffer.",
    )

    input_device_index: int | None = Field(
        default=None,
        description="Index of the input audio device. If None, the default device is used.",
    )
