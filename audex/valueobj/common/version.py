from __future__ import annotations

import functools as ft
import re
import typing as t

from pydantic import Field

from audex.valueobj import BaseValueObject


@ft.total_ordering
class SematicVersion(BaseValueObject):
    major: int = Field(
        ...,
        ge=0,
        le=999,
        description="Major version number",
    )
    minor: int = Field(
        ...,
        ge=0,
        le=999,
        description="Minor version number",
    )
    patch: int = Field(
        ...,
        ge=0,
        le=999,
        description="Patch version number",
    )

    def __str__(self) -> str:
        return self.value

    @property
    def value(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, version_str: str) -> t.Self:
        if not re.match(r"^v?\d+\.\d+\.\d+$", version_str):
            raise ValueError(f"Invalid semantic version string: {version_str}")
        if version_str.startswith("v"):
            version_str = version_str[1:]
        major, minor, patch = map(int, version_str.split("."))
        return cls(major=major, minor=minor, patch=patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SematicVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SematicVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def bump_major(self) -> t.Self:
        self.major += 1
        self.minor = 0
        self.patch = 0
        return self

    def bump_minor(self) -> t.Self:
        self.minor += 1
        self.patch = 0
        return self

    def bump_patch(self) -> t.Self:
        self.patch += 1
        return self
