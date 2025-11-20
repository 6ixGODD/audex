# ruff: noqa: N802
from __future__ import annotations

import datetime
import typing as t

if t.TYPE_CHECKING:
    from audex.entity import Entity


T = t.TypeVar("T")


class FieldSpec(t.Generic[T]):
    """A descriptor for entity fields with validation and default value
    support.

    This descriptor provides type-safe field access with optional validation,
    default values, immutability, and nullable support.

    Attributes:
        default: The default value for the field.
        default_factory: A callable that returns the default value.
        nullable: Whether the field can be None.
        immutable: Whether the field can be modified after initial assignment.
        sortable: Whether the field supports sorting operations.
        name: The public name of the field (set by __set_name__).
        private_name: The private attribute name for storing the value.
        _field_type: Stored type information for stub generation.

    Args:
        default: Default value for the field.
        default_factory: Callable that returns a default value.
        nullable: Whether None is allowed as a value.
        immutable: Whether the field can be modified after being set.
        sortable: Whether the field supports sorting operations.
    """

    def __init__(
        self,
        *,
        default: T | None = None,
        default_factory: t.Callable[[], T] | None = None,
        nullable: bool = False,
        immutable: bool = False,
        sortable: bool = True,
    ) -> None:
        self.default = default
        self.default_factory = default_factory
        self.nullable = nullable
        self.immutable = immutable
        self.sortable = sortable
        self.name: str = ""
        self.private_name: str = ""
        self._field_type: type | None = None  # Store type information

    def __set_name__(self, owner: type, name: str) -> None:
        """Set the field name when the descriptor is assigned to a class
        attribute.

        Args:
            owner: The class that owns this descriptor.
            name: The name of the attribute.
        """
        self.name = name
        self.private_name = f"_field_{name}"

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any] | None = None) -> t.Self: ...
    @t.overload
    def __get__(self, obj: Entity, objtype: type[t.Any] | None = None) -> T: ...
    def __get__(self, obj: Entity | None, objtype: type[t.Any] | None = None) -> T | t.Self:
        """Get the field value."""
        if obj is None:
            return self

        if not hasattr(obj, self.private_name):
            if self.default_factory is not None:
                value = self.default_factory()
            elif self.default is not None:
                value = self.default
            elif self.nullable:
                value = None
            else:
                raise AttributeError(f"Field '{self.name}' has not been set")
            setattr(obj, self.private_name, value)

        return t.cast(T, getattr(obj, self.private_name))

    def __set__(self, obj: Entity, value: T) -> None:
        """Set the field value."""
        if hasattr(obj, self.private_name) and self.immutable:
            raise AttributeError(f"Field '{self.name}' is immutable")

        if value is None and not self.nullable:
            raise ValueError(f"Field '{self.name}' cannot be None")

        setattr(obj, self.private_name, value)

    def __delete__(self, obj: Entity) -> None:
        """Delete the field value."""
        if self.immutable:
            raise AttributeError(f"Field '{self.name}' is immutable")
        if hasattr(obj, self.private_name):
            delattr(obj, self.private_name)


# Modified factory functions to store type information


class StringBackedFieldSpec(FieldSpec[T]):
    """A field descriptor for values that are persisted as strings in
    the database."""


@t.overload
def StringBackedField(
    _field_type: type[T],
    *,
    default: T | None = None,
    default_factory: t.Callable[[], T] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = True,
) -> StringBackedFieldSpec[T]: ...
@t.overload
def StringBackedField(
    _field_type: None = None,
    *,
    default: t.Any | None = None,
    default_factory: t.Callable[[], t.Any] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = True,
) -> StringBackedFieldSpec[t.Any]: ...
def StringBackedField(
    _field_type: type[t.Any] | None = None,
    *,
    default: t.Any | None = None,
    default_factory: t.Callable[[], t.Any] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = True,
) -> t.Any:
    """Factory function to create a StringBackedFieldSpec."""
    field = StringBackedFieldSpec(
        default=default,
        default_factory=default_factory,
        nullable=nullable,
        immutable=immutable,
        sortable=sortable,
    )
    field._field_type = _field_type
    return field


class ListFieldSpec(FieldSpec[list[T]]):
    """A field descriptor for list/collection values."""

    def __init__(
        self,
        *,
        default: list[T] | None = None,
        default_factory: t.Callable[[], list[T]] | None = None,
        nullable: bool = False,
        immutable: bool = False,
        sortable: bool = False,
    ) -> None:
        super().__init__(
            default=default,
            default_factory=default_factory,
            nullable=nullable,
            immutable=immutable,
            sortable=sortable,
        )


@t.overload
def ListField(
    _item_type: type[T],
    *,
    default: list[T] | None = None,
    default_factory: t.Callable[[], list[T]] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = False,
) -> ListFieldSpec[T]: ...
@t.overload
def ListField(
    _item_type: None = None,
    *,
    default: list[t.Any] | None = None,
    default_factory: t.Callable[[], list[t.Any]] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = False,
) -> ListFieldSpec[t.Any]: ...
def ListField(
    _item_type: type[t.Any] | None = None,
    *,
    default: list[t.Any] | None = None,
    default_factory: t.Callable[[], list[t.Any]] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = False,
) -> ListFieldSpec[t.Any]:
    """Factory function to create a ListFieldSpec."""
    field = ListFieldSpec(
        default=default,
        default_factory=default_factory,
        nullable=nullable,
        immutable=immutable,
        sortable=sortable,
    )
    field._field_type = _item_type
    return field


class ForeignFieldSpec(FieldSpec[T]):
    """A field descriptor for foreign/complex type values."""

    def __init__(
        self,
        *,
        default: T | None = None,
        default_factory: t.Callable[[], T] | None = None,
        nullable: bool = False,
        immutable: bool = False,
        sortable: bool = False,
    ) -> None:
        super().__init__(
            default=default,
            default_factory=default_factory,
            nullable=nullable,
            immutable=immutable,
            sortable=sortable,
        )


@t.overload
def ForeignField(
    _field_type: type[T],
    *,
    default: T | None = None,
    default_factory: t.Callable[[], T] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = False,
) -> ForeignFieldSpec[T]: ...
@t.overload
def ForeignField(
    _field_type: None = None,
    *,
    default: t.Any | None = None,
    default_factory: t.Callable[[], t.Any] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = False,
) -> ForeignFieldSpec[t.Any]: ...
def ForeignField(
    _field_type: type[t.Any] | None = None,
    *,
    default: t.Any | None = None,
    default_factory: t.Callable[[], t.Any] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = False,
) -> t.Any:
    """Factory function to create a ForeignFieldSpec."""
    field = ForeignFieldSpec(
        default=default,
        default_factory=default_factory,
        nullable=nullable,
        immutable=immutable,
        sortable=sortable,
    )
    field._field_type = _field_type
    return field


# Keep all other field types as they were
class StringFieldSpec(FieldSpec[str]):
    """A field descriptor for string values."""


def StringField(
    *,
    default: str | None = None,
    default_factory: t.Callable[[], str] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = False,
) -> t.Any:
    return StringFieldSpec(
        default=default,
        default_factory=default_factory,
        nullable=nullable,
        immutable=immutable,
        sortable=sortable,
    )


class IntegerFieldSpec(FieldSpec[int]):
    """A field descriptor for integer values."""


def IntegerField(
    *,
    default: int | None = None,
    default_factory: t.Callable[[], int] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = True,
) -> t.Any:
    return IntegerFieldSpec(
        default=default,
        default_factory=default_factory,
        nullable=nullable,
        immutable=immutable,
        sortable=sortable,
    )


class FloatFieldSpec(FieldSpec[float]):
    """A field descriptor for float values."""


def FloatField(
    *,
    default: float | None = None,
    default_factory: t.Callable[[], float] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = True,
) -> t.Any:
    return FloatFieldSpec(
        default=default,
        default_factory=default_factory,
        nullable=nullable,
        immutable=immutable,
        sortable=sortable,
    )


class BoolFieldSpec(FieldSpec[bool]):
    """A field descriptor for boolean values."""


def BoolField(
    *,
    default: bool | None = None,
    default_factory: t.Callable[[], bool] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = True,
) -> t.Any:
    return BoolFieldSpec(
        default=default,
        default_factory=default_factory,
        nullable=nullable,
        immutable=immutable,
        sortable=sortable,
    )


class DateTimeFieldSpec(FieldSpec[datetime.datetime]):
    """A field descriptor for datetime values."""


def DateTimeField(
    *,
    default: datetime.datetime | None = None,
    default_factory: t.Callable[[], datetime.datetime] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = True,
) -> t.Any:
    return DateTimeFieldSpec(
        default=default,
        default_factory=default_factory,
        nullable=nullable,
        immutable=immutable,
        sortable=sortable,
    )


def Field(
    *,
    default: t.Any | None = None,
    default_factory: t.Callable[[], t.Any] | None = None,
    nullable: bool = False,
    immutable: bool = False,
    sortable: bool = False,
) -> t.Any:
    return FieldSpec(
        default=default,
        default_factory=default_factory,
        nullable=nullable,
        immutable=immutable,
        sortable=sortable,
    )
