from __future__ import annotations

from pydantic import Field

from audex.helper.settings import BaseModel
from audex.utils import UNSET
from audex.utils import Unset


class XFYunCredentialConfig(BaseModel):
    app_id: str | Unset = Field(
        default=UNSET,
        description="XFYun Application ID. Must be provided for authentication.",
    )

    api_key: str | Unset = Field(
        default=UNSET,
        description="XFYun API Key. Must be provided for authentication.",
    )

    api_secret: str | Unset = Field(
        default=UNSET,
        description="XFYun API Secret. Must be provided for authentication.",
    )
