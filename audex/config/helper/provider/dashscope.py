from __future__ import annotations

from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field
from audex.utils import UNSET
from audex.utils import Unset


class DashscopeCredentialConfig(BaseModel):
    api_key: str | Unset = Field(
        default=UNSET,
        description="Dashscope API key for authentication.",
    )
