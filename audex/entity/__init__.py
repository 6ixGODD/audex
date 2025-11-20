from __future__ import annotations

import datetime
import functools as ft
import typing as t

from audex import utils
from audex.entity.fields import DateTimeField
from audex.entity.fields import FieldSpec
from audex.entity.fields import StringField
from audex.filters import FilterBuilder


class EntityMeta(type):
    """Metaclass for Entity that collects all Field descriptors.

    This metaclass automatically discovers all Field descriptors defined in the
    class hierarchy and stores them in the _fields class attribute. It processes
    field inheritance by scanning through the method resolution order (MRO) to
    ensure proper field override behavior.

    Attributes:
        _fields: Class-level dictionary mapping field names to their FieldSpec
            descriptors.

    Example:
        ```python
        class User(Entity):
            username = StringField()
            email = StringField()


        class Admin(User):
            privileges = StringField(default="admin")


        # Admin._fields contains: username, email, privileges
        ```
    """

    _fields: dict[str, FieldSpec[t.Any]]

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, t.Any]) -> EntityMeta:
        """Create a new Entity class with field collection.

        Args:
            name: Name of the class being created.
            bases: Base classes of the new class.
            namespace: Class namespace containing attributes and methods.

        Returns:
            New EntityMeta class with collected fields in _fields attribute.
        """
        cls = super().__new__(mcs, name, bases, namespace)

        # Collect fields from base classes and the current class
        fields: dict[str, FieldSpec[t.Any]] = {}

        # Helper: scan a class __dict__ for Field instances
        def scan_dict_for_fields(obj: type) -> dict[str, FieldSpec[t.Any]]:
            result: dict[str, FieldSpec[t.Any]] = {}
            for k, v in getattr(obj, "__dict__", {}).items():
                if isinstance(v, FieldSpec):
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
            if isinstance(value, FieldSpec):
                fields[key] = value

        cls._fields = fields
        return cls


class Entity(metaclass=EntityMeta):
    """Base entity class with field-based attribute management.

    This class uses Field descriptors to provide type-safe, validated attributes
    with support for defaults, immutability, and nullable values. All entity
    classes should inherit from this base class to get field management
    capabilities.

    The Entity class automatically discovers Field descriptors defined in the
    class hierarchy and manages their values through the metaclass. It provides
    serialization, representation, and field introspection capabilities.

    Attributes:
        _fields: Class-level dictionary of all Field descriptors collected from
            the class hierarchy.

    Example:
        ```python
        class User(Entity):
            username = StringField()
            email = StringField(nullable=True)
            created_at = DateTimeField(default_factory=utils.utcnow)


        user = User(username="john", email="john@example.com")
        print(
            user.dumps()
        )  # {"username": "john", "email": "john@example.com", ...}
        print(
            user
        )  # ENTITY <User(username='john', email='john@example.com', ...)>
        ```
    """

    # Type hints for instance attributes
    if t.TYPE_CHECKING:
        _fields: t.ClassVar[dict[str, FieldSpec[t.Any]]]

    def __init__(self, **kwargs: t.Any) -> None:
        """Initialize an entity with field values.

        Sets field values from the provided keyword arguments. Only fields
        defined in the class hierarchy are accepted.

        Args:
            **kwargs: Field names and their values. Field names must match
                those defined in the class hierarchy.

        Example:
            ```python
            user = User(
                username="john",
                email="john@example.com",
                is_active=True,
            )
            ```
        """
        for field_name, _field in self._fields.items():
            if field_name in kwargs:
                setattr(self, field_name, kwargs[field_name])

    def dumps(self) -> dict[str, t.Any]:
        """Convert entity to a dictionary.

        Serializes all field values to a dictionary. Nested Entity instances
        are recursively converted to dictionaries. Only fields that have been
        set (have a value) are included in the output.

        Returns:
            A dictionary mapping field names to their values. Nested entities
            are recursively converted to dictionaries.

        Example:
            ```python
            user = User(username="john", email="john@example.com")
            data = user.dumps()
            # {"username": "john", "email": "john@example.com", ...}

            # With nested entities
            profile = Profile(bio="Developer")
            user = User(username="john", profile=profile)
            data = user.dumps()
            # {"username": "john", "profile": {"bio": "Developer"}, ...}
            ```
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

        Creates a detailed string showing the class name and all field values
        that have been set.

        Returns:
            A string showing the class name and all field values.

        Example:
            ```python
            user = User(username="john", email="john@example.com")
            print(repr(user))
            # ENTITY <User(username='john', email='john@example.com')>
            ```
        """
        attrs: list[str] = []
        for field_name in self._fields:
            if hasattr(self, f"_field_{field_name}"):
                value = getattr(self, field_name)
                attrs.append(f"{field_name}={value!r}")
        return f"ENTITY <{self.__class__.__name__}({', '.join(attrs)})>"

    @classmethod
    def is_field_sortable(cls, field_name: str) -> bool:
        """Check if a field supports sorting operations.

        Determines whether a field can be used in sorting operations based on
        its field specification.

        Args:
            field_name: The name of the field to check.

        Returns:
            True if the field exists and supports sorting, False otherwise.

        Example:
            ```python
            class User(Entity):
                name = StringField()
                tags = ListField[str](default_factory=list)
                profile = ForeignField[Profile]()


            User.is_field_sortable("name")  # True
            User.is_field_sortable("tags")  # False
            User.is_field_sortable("profile")  # False
            User.is_field_sortable("invalid")  # False
            ```
        """
        field = cls._fields.get(field_name)
        if field is None:
            return False
        return field.sortable


E = t.TypeVar("E", bound=Entity)


def is_field_sortable(entity: Entity, field_name: str) -> bool:
    """Check if a field of an entity instance supports sorting
    operations.

    Convenience function to check field sortability on an entity instance
    rather than the class.

    Args:
        entity: The entity instance.
        field_name: The name of the field to check.

    Returns:
        True if the field exists and supports sorting, False otherwise.

    Example:
        ```python
        user = User(name="John")
        is_field_sortable(user, "name")  # True
        is_field_sortable(user, "tags")  # False
        is_field_sortable(user, "invalid")  # False
        ```
    """
    return entity.__class__.is_field_sortable(field_name)


class BaseEntity(Entity):
    """Base entity with ID and timestamp fields.

    Provides standard fields for entity identification and tracking that are
    commonly needed across all entity types:
    - id: Immutable unique identifier
    - created_at: Immutable creation timestamp
    - updated_at: Mutable last update timestamp

    This class also provides filtering capabilities and equality/hashing based
    on the entity ID.

    Example:
        ```python
        class User(BaseEntity):
            username = StringField()
            email = StringField()


        user = User(username="john", email="john@example.com")
        print(user.id)  # Auto-generated unique ID
        print(user.created_at)  # Timestamp when created

        user.touch()  # Updates updated_at timestamp
        print(user.updated_at)  # Current timestamp
        ```
    """

    # Use TYPE_CHECKING to separate runtime descriptor from type hint
    id: str = StringField(immutable=True, default_factory=utils.gen_id)
    created_at: datetime.datetime = DateTimeField(default_factory=utils.utcnow, immutable=True)
    updated_at: datetime.datetime | None = DateTimeField(nullable=True)

    def touch(self) -> None:
        """Update the updated_at timestamp to the current time.

        Example:
            ```python
            user = User(username="john")
            print(user.updated_at)  # None

            user.touch()
            print(user.updated_at)  # Current timestamp
            ```
        """
        self.updated_at = utils.utcnow()

    @classmethod
    def filter(cls: type[E]) -> FilterBuilder[E]:
        """Create a type-safe filter builder for this entity.

        Returns a FilterBuilder instance that provides a fluent interface for
        constructing type-safe filters and queries.

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

            # Complex filter with sorting
            filter3 = (
                User.filter()
                .created_at.gte(yesterday)
                .username.contains("admin")
                .created_at.desc()
            )
            ```
        """
        return FilterBuilder(cls)

    def __eq__(self, other: object) -> bool:
        """Check equality based on entity ID.

        Two BaseEntity instances are considered equal if they have the same ID,
        regardless of their other field values or class types.

        Args:
            other: Another object to compare with.

        Returns:
            True if both entities have the same ID, False otherwise.

        Example:
            ```python
            user1 = User(id="123", username="john")
            user2 = User(id="123", username="jane")
            user3 = User(id="456", username="john")

            print(user1 == user2)  # True (same ID)
            print(user1 == user3)  # False (different ID)
            ```
        """
        if not isinstance(other, BaseEntity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Compute hash based on entity ID.

        Allows BaseEntity instances to be used in sets and as dictionary keys.
        The hash is based solely on the entity ID.

        Returns:
            Hash value of the entity ID.

        Example:
            ```python
            user1 = User(id="123", username="john")
            user2 = User(id="123", username="jane")

            user_set = {user1, user2}
            print(len(user_set))  # 1 (same hash, considered equal)

            user_dict = {user1: "first", user2: "second"}
            print(user_dict[user1])  # "second" (user2 overwrote user1)
            ```
        """
        return hash(self.id)


P = t.ParamSpec("P")
R = t.TypeVar("R")


class Touchable(t.Protocol):
    """Protocol for entities that can be touched (have their timestamp
    updated).

    This protocol defines the interface for entities that support
    automatic timestamp updating through the touch() method.
    """

    def touch(self) -> None:
        """Update the entity's timestamp."""


TT = t.TypeVar("TT", bound=Touchable)


def touch_after(func: t.Callable[t.Concatenate[TT, P], R]) -> t.Callable[..., R]:
    """Decorator that automatically calls touch() after method
    execution.

    This decorator wraps entity methods to automatically update the updated_at
    timestamp after successful execution. The touch() method is only called if
    the wrapped method completes without raising an exception.

    Args:
        func: The method to wrap. Must be a method of a class that implements
            the Touchable protocol.

    Returns:
        The wrapped method that calls touch() after successful execution.

    Example:
        ```python
        class MyEntity(BaseEntity):
            name = StringField()

            @touch_after
            def update_name(self, name: str) -> None:
                self.name = name
                # touch() is automatically called after this method

            @touch_after
            def risky_operation(self) -> str:
                if some_condition:
                    raise ValueError("Operation failed")
                return "success"
                # touch() only called if no exception is raised


        entity = MyEntity(name="old")
        entity.update_name("new")  # updated_at is automatically set
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
