from __future__ import annotations

import typing as t

from pydantic import Field

from audex.helper.settings import BaseModel


class StoreConfig(BaseModel):
    type: t.Literal["localfile"] = Field(
        default="localfile",
        description="Type of the store.",
    )

    base_url: str = Field(
        default="./store",
        description="Store base URL. In case of 'file' type, it is the local directory path. In case of 'obs' type, it is the OBS bucket URL.",
    )
