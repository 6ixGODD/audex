from __future__ import annotations

import math
import string
import typing as t

from pydantic import Field
from pydantic import field_validator

from audex.helper import hash
from audex.valueobj import SingleValueObject


class Password(SingleValueObject[str]):
    value: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z\d]{8,20}$",
        description="Plain text password, 8-64 characters.",
    )

    @field_validator("value")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v

    def entropy(self) -> float:
        charset_size = 0
        v = self.value
        if any(c.islower() for c in v):
            charset_size += 26
        if any(c.isupper() for c in v):
            charset_size += 26
        if any(c.isdigit() for c in v):
            charset_size += 10
        if any(c in string.punctuation for c in v):
            charset_size += len(string.punctuation)
        if charset_size == 0:
            charset_size = 1
        return len(v) * math.log2(charset_size)

    @staticmethod
    def entropy_to_strength_level(
        entropy: float,
    ) -> t.Literal["weak", "medium", "strong", "very_strong"]:
        if entropy < 40:
            return "weak"
        if entropy < 60:
            return "medium"
        if entropy < 80:
            return "strong"
        return "very_strong"

    def strength_level(self) -> t.Literal["weak", "medium", "strong", "very_strong"]:
        e = self.entropy()
        return self.entropy_to_strength_level(e)

    def hash(self) -> HashedPassword:
        return HashedPassword(value=hash.argon2_hash(self.value))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Password):
            return NotImplemented
        return self.value == other.value


class HashedPassword(SingleValueObject[str]):
    value: str = Field(
        description="Password hashed by Argon2.",
    )

    def verify(self, password: Password) -> bool:
        return hash.argon2_verify(password.value, self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Password):
            return NotImplemented
        return hash.argon2_verify(other.value, self.value)
