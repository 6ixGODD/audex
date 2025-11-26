from __future__ import annotations

import contextlib
import os
import pathlib
import typing as t

from pydantic import Field
from pydantic import model_validator

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

    group_id_path: os.PathLike[str] | str = Field(
        default=".xfyun.vpr.gid",
        description="The file path to read the group ID from if not provided directly.",
    )

    http: HttpClientConfig = Field(
        default_factory=HttpClientConfig,
        description="HTTP client configuration for XFYun VPR service.",
    )

    @model_validator(mode="after")
    def load_group_id_from_file(self) -> t.Self:
        if self.group_id is None:
            with (
                contextlib.suppress(FileNotFoundError),
                pathlib.Path(self.group_id_path).open("r") as f,
            ):
                self.group_id = f.read().strip()
        return self


class UnisoundVPRConfig(BaseModel):
    credential: UnisoundCredentialConfig = Field(
        default_factory=UnisoundCredentialConfig,
        description="Credentials for Unisound VPR service.",
    )

    group_id: str | None = Field(
        default=None,
        description="The group ID for voiceprint recognition.",
    )

    group_id_path: os.PathLike[str] | str = Field(
        default=".unisound.vpr.gid",
        description="The file path to read the group ID from if not provided directly.",
    )

    http: HttpClientConfig = Field(
        default_factory=HttpClientConfig,
        description="HTTP client configuration for Unisound VPR service.",
    )

    @model_validator(mode="after")
    def load_group_id_from_file(self) -> t.Self:
        if self.group_id is None:
            with (
                contextlib.suppress(FileNotFoundError),
                pathlib.Path(self.group_id_path).open("r") as f,
            ):
                self.group_id = f.read().strip()
        return self


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
