from __future__ import annotations

from pydantic import Field

from audex import __title__
from audex import __version__
from audex.helper.settings import BaseModel


class AppConfig(BaseModel):
    app_name: str = Field(
        default=__title__,
        description="The name of the application.",
    )

    app_version: str = Field(
        default=__version__,
        description="The version of the application.",
    )

    debug: bool = Field(
        default=False,
        description="Enable or disable debug mode.",
    )

    native: bool = Field(
        default=False,
        description="Indicates if the application is running in native mode.",
    )

    touch: bool = Field(
        default=False,
        description="Enable or disable touch support.",
    )

    fullscreen: bool = Field(
        default=False,
        description="Enable or disable fullscreen mode.",
    )
