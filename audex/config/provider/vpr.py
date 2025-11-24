from __future__ import annotations

import typing as t

from pydantic import Field

from audex.config.helper.provider.xfyun import XFYunCredentialConfig
from audex.helper.settings import BaseModel


class XFYunVPRConfig(BaseModel):
    credential: XFYunCredentialConfig = Field(
        default_factory=XFYunCredentialConfig,
        description="Credentials for XFYun VPR service.",
    )

    group_id: str | None = Field(
        default=None,
        description="The group ID for voiceprint recognition.",
    )


class UnisoundVPRConfig(BaseModel):
    pass


class VPRConfig(BaseModel):
    provider: t.Literal["xfyun", "unisound"] = Field(
        default="xfyun",
        description="The VPR service provider to use.",
    )

    xfyun: XFYunVPRConfig = Field(
        default_factory=XFYunVPRConfig,
        description="Configuration for the XFYun VPR service.",
    )

    unisound: UnisoundVPRConfig = Field(
        default_factory=UnisoundVPRConfig,
        description="Configuration for the Unisound VPR service.",
    )
