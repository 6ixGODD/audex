from __future__ import annotations

from enum import Enum

from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field


class UIInputMode(str, Enum):
    NEVER = "never"
    ALWAYS = "always"
    AUTO = "auto"


class UIConfig(BaseModel):
    input_mode: UIInputMode = Field(
        default=UIInputMode.AUTO,
        description=(
            "Overlay input mode for touch/tablet devices. "
            "'never': never show overlay input; "
            "'always': always show overlay input on double-click; "
            "'auto': show overlay only when no physical keyboard is detected."
        ),
        linux_default=UIInputMode.AUTO,
        windows_default=UIInputMode.NEVER,
    )
