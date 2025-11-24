from __future__ import annotations

import re
import typing as t

import pydantic as pyd

from audex.valueobj import BaseValueObject


class Phone(BaseValueObject):
    country_code: str = pyd.Field(
        ...,
        min_length=1,
        max_length=5,
        description="Country code of the telephone number",
    )
    number: str = pyd.Field(
        ...,
        min_length=4,
        max_length=15,
        description="Telephone number without country code",
    )

    @pyd.model_validator(mode="after")
    def validate_phone(self) -> t.Self:
        if not self.country_code.isdigit():
            raise ValueError("Country code must contain only digits")
        if not self.number.isdigit():
            raise ValueError("Telephone number must contain only digits")
        return self

    def __str__(self) -> str:
        return f"+{self.country_code} {self.number}"

    @property
    def value(self) -> str:
        """Get the full telephone number in international format.

        Returns:
            A string representing the full telephone number.
        """
        return str(self)

    @classmethod
    def parse(cls, phone_str: str) -> Phone:
        """Create a Telephone object from a string representation.

        Args:
            phone_str: A string in the format "+<country_code> <number>".

        Returns:
            A Telephone object.
        """
        if not re.match(r"^\+\d+ \d+$", phone_str):
            raise ValueError(
                "Invalid phone string format. Expected format: '+<country_code> <number>'"
            )
        country_code, number = phone_str[1:].split(" ", 1)
        return cls(country_code=country_code, number=number)


class CNPhone(Phone):
    @pyd.model_validator(mode="after")
    def validate_chinese_phone(self) -> t.Self:
        if self.country_code != "86":
            raise ValueError("Country code must be '86' for Chinese telephone numbers")
        if len(self.number) != 11 or not self.number.startswith((
            "13",
            "14",
            "15",
            "17",
            "18",
            "19",
        )):
            raise ValueError("Invalid Chinese telephone number format")
        return self
