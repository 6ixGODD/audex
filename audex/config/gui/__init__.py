from __future__ import annotations

from pydantic import Field

from audex.helper.settings import BaseModel


class GUIConfig(BaseModel):
    width: int = Field(
        default=1200,
        description="Width of the GUI window in pixels.",
    )

    height: int = Field(
        default=800,
        description="Height of the GUI window in pixels.",
    )

    fullscreen: bool = Field(
        default=True,
        description="Whether to launch the GUI in fullscreen mode.",
    )
