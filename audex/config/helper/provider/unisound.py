from __future__ import annotations

from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field
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
