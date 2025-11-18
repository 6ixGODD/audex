from __future__ import annotations

import typing as t

from audex.valueobj.common.ops import Op
from audex.valueobj.common.ops import Order

if t.TYPE_CHECKING:
    from audex.entity import Entity
    from audex.entity import Field

E = t.TypeVar("E", bound="Entity")
T = t.TypeVar("T")


class SortSpec:
    """Sort specification for a single field.

    Attributes:
        field: The field name to sort by.
        order: The sort order (ASC or DESC).
    """

    field: str
    order: Order

    __slots__ = ("field", "order")

    def __init__(self, field: str, order: Order = Order.ASC) -> None:
        object.__setattr__(self, "field", field)
        object.__setattr__(self, "order", order)

    def __setattr__(self, key: str, value: t.Any) -> None:
        raise AttributeError("SortSpec instances are immutable")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SortSpec):
            return NotImplemented
        return self.field == other.field and self.order == other.order

    def __hash__(self) -> int:
        return hash((self.field, self.order))

    def __repr__(self) -> str:
        return f"SortSpec(field={self.field!r}, order={self.order.value})"

    def __str__(self) -> str:
        direction = "↑" if self.order == Order.ASC else "↓"
        return f"{self.field} {direction}"


class ConditionSpec:
    """Immutable filter condition.

    Represents a single filter condition with field name, operation, and
    value(s).

    Attributes:
        field: The field name the condition applies to.
        op: The operation (from Op enum).
        value: The value to compare against.
        value2: The second value for operations like BETWEEN (optional).
    """

    field: str
    op: Op
    value: object
    value2: object | None

    __slots__ = ("field", "op", "value", "value2")

    def __init__(self, field: str, op: Op, value: object, value2: object | None = None) -> None:
        object.__setattr__(self, "field", field)
        object.__setattr__(self, "op", op)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "value2", value2)

    def __setattr__(self, key: str, value: t.Any) -> None:
        raise AttributeError("Condition instances are immutable")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConditionSpec):
            return NotImplemented
        return (
            self.field == other.field
            and self.op == other.op
            and self.value == other.value
            and self.value2 == other.value2
        )

    def __hash__(self) -> int:
        return hash((self.field, self.op, self.value, self.value2))

    def __repr__(self) -> str:
        return (
            f"Condition(field={self.field!r}, op={self.op!r}, "
            f"value={self.value!r}, value2={self.value2!r})"
        )

    def __str__(self) -> str:
        if self.value2 is not None:
            return f"{self.field} {self.op.name} {self.value}, {self.value2}"
        return f"{self.field} {self.op.name} {self.value}"


class ConditionGroup:
    """Group of conditions with AND/OR logic.

    Attributes:
        conditions: List of conditions or nested groups.
        operator: "AND" or "OR" - how to combine conditions.
        negated: Whether to negate the entire group.
    """

    __slots__ = ("conditions", "negated", "operator")

    def __init__(
        self,
        conditions: list[ConditionSpec | ConditionGroup] | None = None,
        operator: t.Literal["AND", "OR"] = "AND",
        negated: bool = False,
    ) -> None:
        self.conditions: list[ConditionSpec | ConditionGroup] = conditions or []
        self.operator = operator
        self.negated = negated

    def add(self, condition: ConditionSpec | ConditionGroup) -> None:
        """Add a condition or group to this group."""
        self.conditions.append(condition)

    def __repr__(self) -> str:
        return f"ConditionGroup(operator={self.operator}, conditions={self.conditions})"

    def __str__(self) -> str:
        if not self.conditions:
            return "(empty)"

        inner = f" {self.operator} ".join(
            f"({c})" if isinstance(c, ConditionGroup) else str(c) for c in self.conditions
        )
        s = f"({inner})"
        return f"NOT {s}" if self.negated else s


class Filter:
    """Container for filter conditions with AND/OR support.

    Attributes:
        _condition_group: Root condition group (can contain nested groups).
        _sorts: List of sort specifications.
        _entity_class: The entity class this filter applies to.
    """

    __slots__ = ("_builder", "_condition_group", "_entity_class", "_sorts")

    def __init__(
        self,
        entity_class: type[Entity],
        builder: FilterBuilder[t.Any] | None = None,
    ) -> None:
        self._condition_group = ConditionGroup(operator="AND")
        self._sorts: list[SortSpec] = []
        self._entity_class = entity_class
        self._builder = builder

    @property
    def condition_group(self) -> ConditionGroup:
        """Get the root condition group."""
        return self._condition_group

    @property
    def sorts(self) -> list[SortSpec]:
        """Get the list of sort specifications."""
        return self._sorts

    @property
    def entity_class(self) -> type[Entity]:
        """Get the entity class this filter applies to."""
        return self._entity_class

    @property
    def conditions(self) -> list[ConditionSpec]:
        """Legacy property for backward compatibility.

        Returns flat list of conditions from the root AND group.
        Warning: This loses OR grouping information!
        """
        return [c for c in self._condition_group.conditions if isinstance(c, ConditionSpec)]

    def _add_condition(self, condition: ConditionSpec) -> t.Self:
        """Add a condition to the current filter (AND logic).

        Args:
            condition: The condition to add.

        Returns:
            Self for method chaining.
        """
        self._condition_group.add(condition)
        return self

    def _add_sort(self, sort: SortSpec) -> t.Self:
        """Add a sort specification to the filter.

        Args:
            sort: The sort specification to add.

        Returns:
            Self for method chaining.
        """
        self._sorts.append(sort)
        return self

    def or_(self, *filters: Filter) -> t.Self:
        """Combine conditions with OR logic.

        Creates a new OR group containing:
        - Current filter's conditions
        - All provided filters' conditions

        Args:
            *filters: Other filters to combine with OR logic.

        Returns:
            Self for method chaining.

        Example:
            ```python
            # Find users with username "john" OR email "john@example.com"
            filter1 = user_filter().username.eq("john")
            filter2 = user_filter().email.eq("john@example.com")
            combined = filter1.or_(filter2)

            # Or using method chaining:
            combined = (
                user_filter()
                .username.eq("john")
                .or_(user_filter().email.eq("john@example.com"))
            )
            ```
        """
        # Validate same entity type
        for f in filters:
            if self._entity_class != f._entity_class:
                raise ValueError(
                    f"Cannot combine filters for different entity types: "
                    f"{self._entity_class.__name__} and {f._entity_class.__name__}"
                )

        # Create new OR group
        or_group = ConditionGroup(operator="OR")

        # Add current conditions
        if self._condition_group.conditions:
            if len(self._condition_group.conditions) == 1:
                or_group.add(self._condition_group.conditions[0])
            else:
                # Wrap in AND group if multiple conditions
                or_group.add(
                    ConditionGroup(
                        conditions=self._condition_group.conditions.copy(), operator="AND"
                    )
                )

        # Add other filters' conditions
        for f in filters:
            if f._condition_group.conditions:
                if len(f._condition_group.conditions) == 1:
                    or_group.add(f._condition_group.conditions[0])
                else:
                    or_group.add(
                        ConditionGroup(
                            conditions=f._condition_group.conditions.copy(), operator="AND"
                        )
                    )

        # Replace root group with OR group
        self._condition_group = or_group

        # Merge sorts (keep unique)
        for f in filters:
            for sort in f._sorts:
                if sort not in self._sorts:
                    self._sorts.append(sort)

        return self

    def not_(self) -> Filter:
        """Mark this filter as negated (NOT)."""
        new_filter = Filter(self._entity_class, self._builder)
        new_filter._condition_group = ConditionGroup(
            conditions=self._condition_group.conditions.copy(),
            operator=self._condition_group.operator,
            negated=True,
        )
        new_filter._sorts = self._sorts.copy()
        return new_filter

    def __getattr__(self, name: str) -> FieldFilter[t.Any]:
        """Allow chaining through the original builder.

        This enables: filter().field1.eq(x).field2.eq(y)
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        # Delegate to the builder if available
        if self._builder is not None:
            return getattr(self._builder, name)

        # Fallback: check if field exists
        if name not in self._entity_class._fields:
            raise AttributeError(f"Entity '{self._entity_class.__name__}' has no field '{name}'")

        field = self._entity_class._fields[name]

        from audex.entity import ListField
        from audex.entity import StringBackedField
        from audex.entity import StringField

        if isinstance(field, StringField):
            return StringFieldFilter(name, self)
        if isinstance(field, StringBackedField):
            return StringBackedFieldFilter(name, self)
        if isinstance(field, ListField):
            return ListFieldFilter(name, self)

        return FieldFilter(name, self)

    def __and__(self, other: Filter) -> Filter:
        """Combine two filters with AND logic.

        Args:
            other: Another filter to combine.

        Returns:
            A new filter with combined conditions.

        Raises:
            ValueError: If filters are for different entity types.
        """
        if self._entity_class != other._entity_class:
            raise ValueError(
                f"Cannot combine filters for different entity types: "
                f"{self._entity_class.__name__} and {other._entity_class.__name__}"
            )

        new_filter = Filter(self._entity_class, self._builder)

        # Combine condition groups with AND
        new_filter._condition_group = ConditionGroup(operator="AND")

        # Add self's conditions
        if self._condition_group.conditions:
            if (
                len(self._condition_group.conditions) == 1
                and self._condition_group.operator == "AND"
            ):
                new_filter._condition_group.add(self._condition_group.conditions[0])
            else:
                new_filter._condition_group.add(self._condition_group)

        # Add other's conditions
        if other._condition_group.conditions:
            if (
                len(other._condition_group.conditions) == 1
                and other._condition_group.operator == "AND"
            ):
                new_filter._condition_group.add(other._condition_group.conditions[0])
            else:
                new_filter._condition_group.add(other._condition_group)

        # Merge sorts
        new_filter._sorts = self._sorts + other._sorts

        return new_filter

    def __or__(self, other: Filter) -> Filter:
        """Combine two filters with OR logic (operator overload).

        Args:
            other: Another filter to combine.

        Returns:
            A new filter with OR combination.

        Example:
            ```python
            filter1 = user_filter().username.eq("john")
            filter2 = user_filter().email.eq("john@example.com")
            combined = filter1 | filter2  # Using | operator
            ```
        """
        if self._entity_class != other._entity_class:
            raise ValueError(
                f"Cannot combine filters for different entity types: "
                f"{self._entity_class.__name__} and {other._entity_class.__name__}"
            )

        new_filter = Filter(self._entity_class, self._builder)
        new_filter._condition_group = ConditionGroup(operator="OR")

        # Add self's conditions
        if self._condition_group.conditions:
            if len(self._condition_group.conditions) == 1:
                new_filter._condition_group.add(self._condition_group.conditions[0])
            else:
                new_filter._condition_group.add(
                    ConditionGroup(
                        conditions=self._condition_group.conditions.copy(),
                        operator=self._condition_group.operator,
                    )
                )

        # Add other's conditions
        if other._condition_group.conditions:
            if len(other._condition_group.conditions) == 1:
                new_filter._condition_group.add(other._condition_group.conditions[0])
            else:
                new_filter._condition_group.add(
                    ConditionGroup(
                        conditions=other._condition_group.conditions.copy(),
                        operator=other._condition_group.operator,
                    )
                )

        # Merge sorts
        new_filter._sorts = self._sorts + other._sorts

        return new_filter

    def __invert__(self) -> Filter:
        """Negate the filter (NOT).

        Returns:
            A new filter that is the negation of this filter.
        """
        new_filter = Filter(self._entity_class, self._builder)
        new_filter._condition_group = ConditionGroup(
            conditions=self._condition_group.conditions.copy(),
            operator=self._condition_group.operator,
            negated=True,
        )
        new_filter._sorts = self._sorts.copy()
        return new_filter

    def __repr__(self) -> str:
        return (
            f"FILTER<{self._entity_class.__name__}>({self._condition_group}, sorts={self._sorts})"
        )


class FieldFilter(t.Generic[T]):
    """Type-safe field filter builder.

    Provides comparison methods that return the parent Filter for
    chaining.
    """

    __slots__ = ("_field_name", "_filter")

    def __init__(self, field_name: str, filter_obj: Filter) -> None:
        self._field_name = field_name
        self._filter = filter_obj

    def eq(self, value: T) -> Filter:
        """Field equals value."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.EQ, value))
        return self._filter

    def ne(self, value: T) -> Filter:
        """Field not equals value."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.NE, value))
        return self._filter

    def gt(self, value: T) -> Filter:
        """Field greater than value."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.GT, value))
        return self._filter

    def lt(self, value: T) -> Filter:
        """Field less than value."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.LT, value))
        return self._filter

    def gte(self, value: T) -> Filter:
        """Field greater than or equal to value."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.GTE, value))
        return self._filter

    def lte(self, value: T) -> Filter:
        """Field less than or equal to value."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.LTE, value))
        return self._filter

    def in_(self, values: t.Sequence[T]) -> Filter:
        """Field in list of values."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.IN, values))
        return self._filter

    def nin(self, values: t.Sequence[T]) -> Filter:
        """Field not in list of values."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.NIN, values))
        return self._filter

    def between(self, value1: T, value2: T) -> Filter:
        """Field between two values (inclusive)."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.BETWEEN, value1, value2))
        return self._filter

    def is_null(self) -> Filter:
        """Field is NULL/None."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.EQ, None))
        return self._filter

    def is_not_null(self) -> Filter:
        """Field is not NULL/None."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.NE, None))
        return self._filter

    def asc(self) -> Filter:
        """Sort field in ascending order."""
        self._filter._add_sort(SortSpec(self._field_name, Order.ASC))
        return self._filter

    def desc(self) -> Filter:
        """Sort field in descending order."""
        self._filter._add_sort(SortSpec(self._field_name, Order.DESC))
        return self._filter

    def __repr__(self) -> str:
        return f"FieldFilter<{self._field_name}>()"


class StringFieldFilter(FieldFilter[str]):
    """String-specific field filter with additional operations."""

    def contains(self, value: str) -> Filter:
        """Field contains substring."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.CONTAINS, value))
        return self._filter

    def startswith(self, value: str) -> Filter:
        """Field starts with substring (uses ^prefix pattern)."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.CONTAINS, f"^{value}"))
        return self._filter

    def endswith(self, value: str) -> Filter:
        """Field ends with substring (uses suffix$ pattern)."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.CONTAINS, f"{value}$"))
        return self._filter


class StringBackedFieldFilter(FieldFilter[T]):
    """Filter for fields that are persisted as strings but have custom
    types.

    Supports string operations like contains, startswith, endswith.
    """

    def contains(self, value: str) -> Filter:
        """Field contains substring."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.CONTAINS, value))
        return self._filter

    def startswith(self, value: str) -> Filter:
        """Field starts with substring (uses ^prefix pattern)."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.CONTAINS, f"^{value}"))
        return self._filter

    def endswith(self, value: str) -> Filter:
        """Field ends with substring (uses suffix$ pattern)."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.CONTAINS, f"{value}$"))
        return self._filter


class ListFieldFilter(FieldFilter[list[T]]):
    """Filter for list/collection fields.

    Supports contains operation to check if a value exists in the list.
    """

    def has(self, value: T) -> Filter:
        """Check if list contains value."""
        self._filter._add_condition(ConditionSpec(self._field_name, Op.HAS, value))
        return self._filter


class FilterBuilder(t.Generic[E]):
    """Type-safe filter builder for entities.

    This class dynamically creates properties for each field in the entity,
    allowing type-safe filter construction with IDE autocomplete.

    Example:
        ```python
        # Single condition
        filter1 = User.filter().username.eq("john")

        # Multiple conditions (AND - chained)
        filter2 = (
            User.filter()
            .username.contains("test")
            .is_active.eq(True)
            .tier.in_([UserTier.PREMIUM, UserTier.VIP])
        )

        # OR combination - Method 1: or_() method
        filter3 = (
            User.filter()
            .username.eq("john")
            .or_(User.filter().email.eq("john@example.com"))
        )

        # OR combination - Method 2: | operator
        filter4 = User.filter().username.eq(
            "john"
        ) | User.filter().email.eq("john@example.com")

        # Complex: (username = "john" OR email = "john@ex.com") AND is_active = True
        filter5 = (
            User.filter().username.eq("john")
            | User.filter().email.eq("john@example.com")
        ) & User.filter().is_active.eq(True)

        # Combining filters with &
        active_filter = User.filter().is_active.eq(True)
        premium_filter = User.filter().tier.eq(UserTier.PREMIUM)
        combined = active_filter & premium_filter
        ```
    """

    __slots__ = ("_entity_class", "_filter")

    def __init__(self, entity_class: type[E]) -> None:
        object.__setattr__(self, "_entity_class", entity_class)
        # Pass self to Filter so it can delegate back to us
        filter_obj = Filter(entity_class, builder=self)
        object.__setattr__(self, "_filter", filter_obj)

    def __getattr__(self, name: str) -> FieldFilter[t.Any]:
        """Dynamically create field filters for entity fields.

        Args:
            name: The field name to filter on.

        Returns:
            A FieldFilter for the requested field.

        Raises:
            AttributeError: If the field doesn't exist in the entity.
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        entity_class: type[E] = object.__getattribute__(self, "_entity_class")
        if name not in entity_class._fields:
            raise AttributeError(f"Entity '{entity_class.__name__}' has no field '{name}'")

        field: Field[t.Any] = entity_class._fields[name]
        filter_obj: Filter = object.__getattribute__(self, "_filter")

        # Return appropriate filter type based on field type
        from audex.entity import ListField
        from audex.entity import StringBackedField
        from audex.entity import StringField

        if isinstance(field, StringField):
            return StringFieldFilter(name, filter_obj)
        if isinstance(field, StringBackedField):
            return StringBackedFieldFilter(name, filter_obj)
        if isinstance(field, ListField):
            return ListFieldFilter(name, filter_obj)

        return FieldFilter(name, filter_obj)

    def __setattr__(self, name: str, value: t.Any) -> None:
        """Prevent attribute assignment to maintain immutability."""
        raise AttributeError("FilterBuilder attributes cannot be modified")

    def build(self) -> Filter:
        """Build and return the final Filter object.

        Returns:
            The constructed Filter with all conditions.

        Note:
            This method is optional. The Filter is automatically returned
            after each condition method call, so you can use the filter
            directly without calling build().
        """
        return object.__getattribute__(self, "_filter")
