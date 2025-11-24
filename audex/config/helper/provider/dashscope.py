from __future__ import annotations

from pydantic import Field

from audex.helper.settings import BaseModel
from audex.utils import UNSET
from audex.utils import Unset


class DashscopeCredentialConfig(BaseModel):
    api_key: str | Unset = Field(
        default=UNSET,
        description="Dashscope API key for authentication.",
    )
