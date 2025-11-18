from __future__ import annotations

import datetime
import functools as ft
import typing as t

from audex import utils
from audex.filters import FilterBuilder
from audex.valueobj.common.version import SematicVersion

T = t.TypeVar("T")


class Field(t.Generic[T]):
    """A descriptor for entity fields with validation and default value
    support.

    This descriptor provides type-safe field access with optional validation,
    default values, immutability, and nullable support.

    Attributes:
        default: The default value for the field.
        default_factory: A callable that returns the default value.
        nullable: Whether the field can be None.
        immutable: Whether the field can be modified after initial assignment.
        name: The public name of the field (set by __set_name__).
        private_name: The private attribute name for storing the value.

    Args:
        default: Default value for the field.
        default_factory: Callable that returns a default value.
        nullable: Whether None is allowed as a value.
        immutable: Whether the field can be modified after being set.
    """

    def __init__(
        self,
        *,
        default: T | None = None,
        default_factory: t.Callable[[], T] | None = None,
        nullable: bool = False,
        immutable: bool = False,
    ) -> None:
        self.default = default
        self.default_factory = default_factory
        self.nullable = nullable
        self.immutable = immutable
        self.name: str = ""
        self.private_name: str = ""

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
        """Get the field value.

        Args:
            obj: The instance accessing the field, or None for class-level
                access.
            objtype: The type of the instance.

        Returns:
            The Field descriptor itself for class-level access, or the field
            value for instance-level access.

        Raises:
            AttributeError: If the field has not been set and no default is
                available.
        """
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
        """Set the field value.

        Args:
            obj: The instance to set the field on.
            value: The value to set.

        Raises:
            AttributeError: If the field is immutable and already set.
            ValueError: If value is None and the field is not nullable.
        """
        if hasattr(obj, self.private_name) and self.immutable:
            raise AttributeError(f"Field '{self.name}' is immutable")

        if value is None and not self.nullable:
            raise ValueError(f"Field '{self.name}' cannot be None")

        setattr(obj, self.private_name, value)

    def __delete__(self, obj: Entity) -> None:
        """Delete the field value.

        Args:
            obj: The instance to delete the field from.

        Raises:
            AttributeError: If the field is immutable.
        """
        if self.immutable:
            raise AttributeError(f"Field '{self.name}' is immutable")
        if hasattr(obj, self.private_name):
            delattr(obj, self.private_name)


class StringField(Field[str]):
    """A field descriptor for string values."""


class StringBackedField(Field[T]):
    """A field descriptor for values that are persisted as strings in
    the database.

    This is useful for value objects that have a string representation in the database
    but should support string-based filtering operations like contains, startswith, etc.

    Example:
        class User(BaseEntity):
            email = StringBackedField[EmailAddress]()
            ip_address = StringBackedField[IPAddress]()
    """


class ListField(Field[list[T]]):
    """A field descriptor for list/collection values.

    Supports contains operations to check if a value exists in the list.

    Example:
        class User(BaseEntity):
            tags = ListField[str](default_factory=list)
            roles = ListField[Role](default_factory=list)
    """


class IntegerField(Field[int]):
    """A field descriptor for integer values."""


class FloatField(Field[float]):
    """A field descriptor for float values."""


class BoolField(Field[bool]):
    """A field descriptor for boolean values."""


class DateTimeField(Field[datetime.datetime]):
    """A field descriptor for datetime values."""


class ForeignField(Field[T]):
    """A field descriptor for foreign/complex type values."""


class EntityMeta(type):
    """Metaclass for Entity that collects all Field descriptors.

    This metaclass automatically discovers all Field descriptors defined
    in the class hierarchy and stores them in the _fields class
    attribute.
    """

    _fields: dict[str, Field[t.Any]]

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, t.Any]) -> EntityMeta:
        cls = super().__new__(mcs, name, bases, namespace)

        # Collect fields from base classes and the current class
        fields: dict[str, Field[t.Any]] = {}

        # Helper: scan a class __dict__ for Field instances
        def scan_dict_for_fields(obj):
            result: dict[str, Field[t.Any]] = {}
            for k, v in getattr(obj, "__dict__", {}).items():
                if isinstance(v, Field):
                    result[k] = v
            return result

        # Collect fields from base classes in inheritance order (base classes first).
        # This makes later subclass definitions override earlier ones.
        for base in reversed(cls.__mro__[:-1]):  # exclude 'object'
            # If base has _fields prepared by EntityMeta, reuse it (fast, canonical).
            base_fields = getattr(base, "_fields", None)
            if isinstance(base_fields, dict):
                # copy to avoid accidental mutation
                for k, v in base_fields.items():
                    fields[k] = v
            else:
                # Fallback: scan base.__dict__ for Field descriptors (covers mixins)
                scanned = scan_dict_for_fields(base)
                for k, v in scanned.items():
                    # Only add when not already present (earlier base or subclass will override)
                    if k not in fields:
                        fields[k] = v

        # Finally, collect fields declared on this class namespace (these override bases).
        for key, value in namespace.items():
            if isinstance(value, Field):
                fields[key] = value

        cls._fields = fields
        return cls


class Entity(metaclass=EntityMeta):
    """Base entity class with field-based attribute management.

    This class uses Field descriptors to provide type-safe, validated attributes
    with support for defaults, immutability, and nullable values.

    Attributes:
        _fields: Class-level dictionary of all Field descriptors.
    """

    # Type hints for instance attributes
    if t.TYPE_CHECKING:
        _fields: t.ClassVar[dict[str, Field[t.Any]]]

    def __init__(self, **kwargs: t.Any) -> None:
        """Initialize an entity with field values.

        Args:
            **kwargs: Field names and their values.
        """
        for field_name, _field in self._fields.items():
            if field_name in kwargs:
                setattr(self, field_name, kwargs[field_name])

    def dumps(self) -> dict[str, t.Any]:
        """Convert entity to a dictionary.

        Returns:
            A dictionary mapping field names to their values. Nested entities
            are recursively converted to dictionaries.
        """
        result: dict[str, t.Any] = {}
        for field_name in self._fields:
            if hasattr(self, f"_field_{field_name}"):
                value = getattr(self, field_name)
                if isinstance(value, Entity):
                    value = value.dumps()
                result[field_name] = value
        return result

    def __repr__(self) -> str:
        """Generate a string representation of the entity.

        Returns:
            A string showing the class name and all field values.
        """
        attrs: list[str] = []
        for field_name in self._fields:
            if hasattr(self, f"_field_{field_name}"):
                value = getattr(self, field_name)
                attrs.append(f"{field_name}={value!r}")
        return f"ENTITY <{self.__class__.__name__}({', '.join(attrs)})>"


E = t.TypeVar("E", bound=Entity)


class BaseEntity(Entity):
    """Base entity with ID and timestamp fields.

    Provides standard fields for entity identification and tracking:
    - id: Immutable unique identifier
    - created_at: Immutable creation timestamp
    - updated_at: Mutable last update timestamp
    """

    # Use TYPE_CHECKING to separate runtime descriptor from type hint
    if t.TYPE_CHECKING:
        id: str
        created_at: datetime.datetime
        updated_at: datetime.datetime | None
    else:
        id = StringField(immutable=True, default_factory=utils.gen_id)
        created_at = DateTimeField(default_factory=utils.utcnow, immutable=True)
        updated_at = DateTimeField(nullable=True)

    def touch(self) -> None:
        """Update the updated_at timestamp to the current time."""
        self.updated_at = utils.utcnow()

    @classmethod
    def filter(cls: type[E]) -> FilterBuilder[E]:
        """Create a type-safe filter builder for this entity.

        Returns:
            A FilterBuilder instance for constructing filters.

        Example:
            ```python
            # Simple filter
            filter1 = User.filter().username.eq("john")

            # Chained conditions
            filter2 = (
                User.filter()
                .is_active.eq(True)
                .tier.in_([UserTier.PREMIUM, UserTier.VIP])
            )
            ```
        """
        return FilterBuilder(cls)

    def __eq__(self, other: object) -> bool:
        """Check equality based on entity ID.

        Args:
            other: Another object to compare with.

        Returns:
            True if both entities have the same ID, False otherwise.
        """
        if not isinstance(other, BaseEntity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Compute hash based on entity ID.

        Returns:
            Hash value of the entity ID.
        """
        return hash(self.id)


P = t.ParamSpec("P")
R = t.TypeVar("R")


class Touchable(t.Protocol):
    """Protocol for entities that can be touched (have their timestamp
    updated)."""

    def touch(self) -> None: ...


TT = t.TypeVar("TT", bound=Touchable)


def touch_after(func: t.Callable[t.Concatenate[TT, P], R]) -> t.Callable[..., R]:
    """Decorator that automatically calls touch() after method
    execution.

    This decorator wraps entity methods to automatically update the updated_at
    timestamp after successful execution.

    Args:
        func: The method to wrap.

    Returns:
        The wrapped method that calls touch() after execution.

    Example:
        ```python
        class MyEntity(BaseEntity):
            @touch_after
            def update_name(self, name: str) -> None:
                self.name = name
        ```
    """

    @ft.wraps(func)
    def wrapper(self: TT, *args: P.args, **kwargs: P.kwargs) -> R:
        try:
            result = func(self, *args, **kwargs)
        except Exception:
            raise
        else:
            self.touch()
            return result

    return wrapper  # type: ignore[return-value]


class SoftDeleteMixin:
    """Mixin providing soft delete functionality.

    Adds a deleted_at timestamp field and methods for soft deletion and
    restoration. Entities with this mixin can be marked as deleted without
    removing them from the database.

    Note: This must be mixed with BaseEntity or its subclasses.
    """

    if t.TYPE_CHECKING:
        deleted_at: datetime.datetime | None
        touch: t.Callable[[], None]
    else:
        deleted_at = DateTimeField(nullable=True)

    @property
    def is_deleted(self) -> bool:
        """Check if the entity is soft deleted.

        Returns:
            True if deleted_at is set, False otherwise.
        """
        return self.deleted_at is not None

    @touch_after
    def soft_delete(self) -> None:
        """Mark the entity as deleted by setting deleted_at to current
        time."""
        self.deleted_at = utils.utcnow()

    @touch_after
    def restore(self) -> None:
        """Restore a soft deleted entity by clearing the deleted_at
        timestamp."""
        self.deleted_at = None


class ReleasableMixin:
    """Mixin providing release tracking functionality.

    Adds fields and methods for tracking the release time and version.

    Note: This must be mixed with BaseEntity or its subclasses.
    """

    if t.TYPE_CHECKING:
        released_at: datetime.datetime | None
        release_version: SematicVersion | None
        touch: t.Callable[[], None]

    else:
        released_at = DateTimeField(nullable=True)
        release_version = StringBackedField[SematicVersion](nullable=True)

    @touch_after
    def release(
        self,
        version: SematicVersion | None = None,
        at: datetime.datetime | None = None,
    ) -> None:
        """Update the release timestamp and version.

        Args:
            version: The version being released. Defaults to None if not provided.
            at: The timestamp of the release. Defaults to current time if None.
        """
        self.released_at = at or utils.utcnow()
        self.release_version = (
            version or self.release_version.bump_minor()
            if self.release_version
            else SematicVersion(major=1, minor=0, patch=0)
        )
