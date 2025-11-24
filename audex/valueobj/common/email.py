from __future__ import annotations

from pydantic import Field

from audex.valueobj import SingleValueObject


class Email(SingleValueObject[str]):
    value: str = Field(
        ...,
        description="A valid email address",
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    )

    def __str__(self) -> str:
        return self.value
