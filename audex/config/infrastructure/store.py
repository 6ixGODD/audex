from __future__ import annotations

import typing as t

from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field


class StoreConfig(BaseModel):
    type: t.Literal["localfile"] = Field(
        default="localfile",
        description="Type of the store.",
    )

    base_url: str = Field(
        default="store",
        description="Store base URL. In case of 'file' type, it is the local directory path. In case of 'obs' type, it is the OBS bucket URL.",
        system_default="store",
        system_path_type="data",
    )
