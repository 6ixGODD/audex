from __future__ import annotations

from pydantic import Field

from audex.helper.settings import BaseModel
from audex.utils import UNSET
from audex.utils import Unset


class UnisoundCredentialConfig(BaseModel):
    appkey: str | Unset = Field(
        default=UNSET,
        description="Unisound App Key",
    )

    secret: str | Unset = Field(
        default=UNSET,
        description="Unisound Secret",
    )
