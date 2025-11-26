from __future__ import annotations

import abc
import builtins
import enum
import typing as t

import pydantic as pyd

from audex.exceptions import ValidationError


class BaseValueObject(pyd.BaseModel, abc.ABC):
    model_config: t.ClassVar[pyd.ConfigDict] = pyd.ConfigDict(
        validate_assignment=True,  # Validate on assignment
        extra="forbid",  # Disallow extra fields
    )

    @pyd.model_validator(mode="wrap")
    @classmethod
    def reraise(cls, data: t.Any, handler: pyd.ModelWrapValidatorHandler[t.Self]) -> t.Self:
        try:
            return handler(data)
        except pyd.ValidationError as e:
            raise ValidationError.from_pydantic_validation_err(e) from e

    def __repr__(self) -> str:
        field_reprs = ", ".join(
            f"{field_name}={getattr(self, field_name)!r}"
            for field_name in self.model_fields  # type: ignore
        )
        return f"VALUEOBJECT <{self.__class__.__name__}({field_reprs})>"


T = t.TypeVar("T")


class SingleValueObject(BaseValueObject, t.Generic[T]):
    value: T

    @classmethod
    def parse(cls, value: T, *, validate: bool = True) -> t.Self:
        return cls(value=value) if validate else cls.model_construct(value=value)


class PaginationParams(BaseValueObject):
    page: int = pyd.Field(
        default=1,
        ge=1,
        description="Page number for pagination, starting from 1",
    )

    limit: int = pyd.Field(
        default=10,
        ge=1,
        le=100,
        description="Number of items per page, between 1 and 100",
    )


class EnumValueObject(enum.Enum):
    @classmethod
    def parse(cls, value: str) -> t.Self:
        try:
            return cls(value)
        except ValueError as e:
            raise ValidationError(
                f"Invalid value '{value}' for enum '{cls.__name__}'. "
                f"Allowed values are: {cls.list()}",
                reason="invalid_enum_value",
            ) from e

    @classmethod
    def list(cls) -> builtins.list[str]:
        return [member.value for member in cls]

    def __repr__(self) -> str:
        return f"ENUM VALUEOBJECT <{self.__class__.__name__}.{self.name}>"

    def __str__(self) -> str:
        return str(self.value)
