from __future__ import annotations

import typing as t

from pydantic import Field

from audex.config.helper.client.http import HttpClientConfig
from audex.config.helper.provider.unisound import UnisoundCredentialConfig
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

    http: HttpClientConfig = Field(
        default_factory=HttpClientConfig,
        description="HTTP client configuration for XFYun VPR service.",
    )


class UnisoundVPRConfig(BaseModel):
    credential: UnisoundCredentialConfig = Field(
        default_factory=UnisoundCredentialConfig,
        description="Credentials for Unisound VPR service.",
    )

    group_id: str | None = Field(
        default=None,
        description="The group ID for voiceprint recognition.",
    )

    http: HttpClientConfig = Field(
        default_factory=HttpClientConfig,
        description="HTTP client configuration for Unisound VPR service.",
    )


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
