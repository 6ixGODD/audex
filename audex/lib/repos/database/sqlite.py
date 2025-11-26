from __future__ import annotations

import abc
import typing as t
import warnings

import sqlalchemy as sa

from audex.filters import ConditionGroup
from audex.filters import ConditionSpec
from audex.filters import Filter
from audex.filters import SortSpec
from audex.helper.mixin import LoggingMixin
from audex.lib.database.sqlite import SQLite
from audex.lib.repos import BaseRepository
from audex.lib.repos import E
from audex.lib.repos.tables import BaseTable
from audex.valueobj.common.ops import Op
from audex.valueobj.common.ops import Order


class SQLiteQuerySpec(t.NamedTuple):
    """Container for SQLite query specifications.

    Attributes:
        where: List of SQLAlchemy where clause expressions.
        order_by: List of SQLAlchemy order by clause expressions.
    """

    where: list[sa.ColumnElement[bool]]
    order_by: list[sa.UnaryExpression[t.Any]]


class SQLiteRepository(LoggingMixin, BaseRepository[E], abc.ABC):
    """Abstract base repository for SQLite operations with filter
    support.

    This class provides common functionality for converting type-safe filters
    to SQLAlchemy queries and defines the standard CRUD interface that all
    SQLite repositories must implement.

    Attributes:
        sqlite: SQLite connection instance.
        logger: Logger instance for this repository.
        __table__: The SQLAlchemy Table/Model class associated with this repository.
        __tablename__: The name of the SQLite table used by this repository.

    Args:
        sqlite: SQLite connection instance.

    Example:
        ```python
        class UserRepository(SQLiteRepository[User]):
            __table__ = UserTable
            __tablename__ = "users"

            async def create(self, data: User) -> str:
                async with self.sqlite.session() as session:
                    db_obj = self.entity_to_table(data)
                    session.add(db_obj)
                    await session.commit()
                    await session.refresh(db_obj)
                    return str(db_obj.id)

            async def list(
                self,
                filter: Filter | None = None,
            ) -> list[User]:
                spec = self.build_query_spec(filter)
                async with self.sqlite.session() as session:
                    stmt = sa.select(self.__table__)
                    for clause in spec.where:
                        stmt = stmt.where(clause)
                    for order in spec.order_by:
                        stmt = stmt.order_by(order)
                    result = await session.execute(stmt)
                    db_objs = result.scalars().all()
                    return [
                        self.table_to_entity(obj) for obj in db_objs
                    ]
        ```
    """

    __logtag__ = "audex.lib.repos.sqlite"
    __repotype__ = "sqlite"
    __table__: t.ClassVar[type[BaseTable[t.Any]]]
    __tablename__: t.ClassVar[str]

    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "__table__") or not issubclass(cls.__table__, BaseTable):
            raise NotImplementedError(
                "__table__ must be defined and be a subclass of BaseTable in SQLiteRepository subclasses."
            )
        if not hasattr(cls, "__tablename__") or not isinstance(cls.__tablename__, str):
            cls.__tablename__ = cls.__table__.__tablename__
            warnings.warn(
                f"__tablename__ not defined in {cls.__name__}, defaulting to {cls.__tablename__}",
                UserWarning,
                stacklevel=2,
            )

    def __init__(self, sqlite: SQLite) -> None:
        super().__init__()
        self.sqlite = sqlite

    def build_query_spec(self, filter: t.Optional[Filter]) -> SQLiteQuerySpec:  # noqa
        """Convert Filter to SQLAlchemy query specifications for SQLite.

        This method translates the type-safe Filter object into SQLAlchemy
        where clauses and order by clauses that can be used with SQLite
        queries.

        Args:
            filter: The filter to convert, or None for no filtering/sorting.

        Returns:
            A SQLiteQuerySpec containing both where clauses and order by
            clauses. Returns empty lists if filter is None.

        Examples:
            Simple query with sort:
            ```python
            filter = user_filter().username.eq("john").created_at.desc()
            spec = repo.build_query_spec(filter)
            stmt = sa.select(UserTable)
            for clause in spec.where:
                stmt = stmt.where(clause)
            for order in spec.order_by:
                stmt = stmt.order_by(order)
            ```

            Multiple conditions with multiple sorts:
            ```python
            filter = (
                user_filter()
                .is_active.eq(True)
                .tier.eq(UserTier.PREMIUM)
                .created_at.desc()
                .username.asc()
            )
            spec = repo.build_query_spec(filter)
            # Will generate appropriate WHERE and ORDER BY clauses
            ```

            OR conditions:
            ```python
            filter = user_filter().username.eq(
                "john"
            ) | user_filter().email.eq("john@example.com")
            spec = repo.build_query_spec(filter)
            # Generates: WHERE username = 'john' OR email = 'john@example.com'
            ```

            NOT conditions:
            ```python
            # Single field negation
            filter = ~user_filter().username.eq("john")
            spec = repo.build_query_spec(filter)
            # Generates: WHERE NOT (username = 'john')

            # Multiple fields negation
            filter = ~(
                user_filter().username.eq("john").is_active.eq(True)
            )
            spec = repo.build_query_spec(filter)
            # Generates: WHERE NOT (username = 'john' AND is_active = 1)

            # NOT with OR
            filter = ~(
                user_filter().username.eq("john")
                | user_filter().email.eq("john@ex.com")
            )
            spec = repo.build_query_spec(filter)
            # Generates: WHERE NOT (username = 'john' OR email = 'john@ex.com')
            ```

            Complex nested conditions:
            ```python
            filter = (
                user_filter().tier.eq(UserTier.PREMIUM)
                | user_filter().tier.eq(UserTier.VIP)
            ) & user_filter().is_active.eq(True)
            spec = repo.build_query_spec(filter)
            # Generates: WHERE (tier = 'premium' OR tier = 'vip') AND is_active = 1
            ```

            List has (single element in JSON array):
            ```python
            filter = user_filter().tags.has("premium")
            spec = repo.build_query_spec(filter)
            # Generates: WHERE json_extract(tags, '$') LIKE '%"premium"%'
            ```

            List contains (subset check - database array contains all specified elements):
            ```python
            filter = user_filter().tags.contains([
                "premium",
                "verified",
            ])
            spec = repo.build_query_spec(filter)
            # Generates multiple json_extract checks for each element
            ```

        Notes:
            - Where: Supports nested AND/OR/NOT logic
            - Order: Order is preserved as specified in the filter chain
            - Uses SQLAlchemy's expression language for type safety
            - List fields stored as JSON use SQLite JSON1 extension functions
            - List HAS: Uses json_extract with LIKE for single element existence
            - List CONTAINS: Uses multiple json_extract checks for subset verification
            - NOT operations use SQLAlchemy's not_() function
            - SQLite doesn't have native JSON operators like PostgreSQL
        """
        where_clauses = self.build_where(filter)
        order_by_clauses = self.build_order_by(filter)
        return SQLiteQuerySpec(
            where=where_clauses,
            order_by=order_by_clauses,
        )

    def build_where(self, filter: t.Optional[Filter]) -> list[sa.ColumnElement[bool]]:  # noqa
        """Convert Filter conditions to SQLAlchemy where clauses for
        SQLite.

        This method translates the filter conditions into SQLAlchemy
        where clause expressions that can be used with SQLite queries.
        Supports nested AND/OR/NOT logic through ConditionGroup.

        Args:
            filter: The filter to convert, or None for no filtering.

        Returns:
            A list of SQLAlchemy ColumnElement expressions for WHERE clauses.
            Returns empty list if filter is None or has no conditions.

        Examples:
            Simple equality:
            ```python
            filter = user_filter().username.eq("john")
            clauses = repo.build_where(filter)
            # Result: [UserTable.username == "john"]
            ```

            Multiple AND conditions:
            ```python
            filter = (
                user_filter()
                .is_active.eq(True)
                .tier.eq(UserTier.PREMIUM)
            )
            clauses = repo.build_where(filter)
            # Result: [UserTable.is_active == True, UserTable.tier == "premium"]
            ```

            OR conditions:
            ```python
            filter = user_filter().username.eq(
                "john"
            ) | user_filter().email.eq("john@example.com")
            clauses = repo.build_where(filter)
            # Result: [
            #     or_(
            #         UserTable.username == "john",
            #         UserTable.email == "john@example.com"
            #     )
            # ]
            ```

            NOT conditions:
            ```python
            # Single field negation
            filter = ~user_filter().username.eq("john")
            clauses = repo.build_where(filter)
            # Result: [not_(UserTable.username == "john")]

            # Multiple AND conditions negation
            filter = ~(
                user_filter().username.eq("john").is_active.eq(True)
            )
            clauses = repo.build_where(filter)
            # Result: [
            #     not_(
            #         and_(
            #             UserTable.username == "john",
            #             UserTable.is_active == True
            #         )
            #     )
            # ]

            # NOT with OR
            filter = ~(
                user_filter().username.eq("john")
                | user_filter().email.eq("john@ex.com")
            )
            clauses = repo.build_where(filter)
            # Result: [
            #     not_(
            #         or_(
            #             UserTable.username == "john",
            #             UserTable.email == "john@ex.com"
            #         )
            #     )
            # ]
            ```

            Complex nested conditions:
            ```python
            filter = (
                user_filter().tier.eq(UserTier.PREMIUM)
                | user_filter().tier.eq(UserTier.VIP)
            ) & user_filter().is_active.eq(True)
            clauses = repo.build_where(filter)
            # Result: [
            #     and_(
            #         or_(
            #             UserTable.tier == "premium",
            #             UserTable.tier == "vip"
            #         ),
            #         UserTable.is_active == True
            #     )
            # ]
            ```

            List has (single element in JSON array):
            ```python
            filter = user_filter().tags.has("premium")
            clauses = repo.build_where(filter)
            # Result: Uses SQLite JSON1 extension
            # SQL: WHERE json_extract(tags, '$') LIKE '%"premium"%'
            ```

            List contains (subset check - database array contains all specified elements):
            ```python
            filter = user_filter().tags.contains([
                "premium",
                "verified",
            ])
            clauses = repo.build_where(filter)
            # Result: Multiple JSON checks for each element
            # SQL: WHERE json_extract(tags, '$') LIKE '%"premium"%'
            #       AND json_extract(tags, '$') LIKE '%"verified"%'
            ```

        Notes:
            - Supports recursive AND/OR/NOT nesting
            - All conditions are properly parenthesized
            - String CONTAINS operations use case-insensitive LIKE
            - List HAS operations use SQLite JSON1 extension with LIKE
            - List CONTAINS operations check each element individually
            - NOT operations use SQLAlchemy's not_() function
            - SQLite boolean values are stored as integers (0/1)
        """
        if filter is None or not object.__getattribute__(filter, "condition_group").conditions:
            return []

        clause = self._build_group_clause(object.__getattribute__(filter, "condition_group"))
        return [clause] if clause is not None else []

    def _build_group_clause(self, group: ConditionGroup) -> t.Optional[sa.ColumnElement[bool]]:  # noqa
        """Recursively build SQLAlchemy clause from a ConditionGroup.

        Args:
            group: The condition group to convert.

        Returns:
            A SQLAlchemy ColumnElement expression, or None if group is empty.

        Examples:
            AND group:
            ```python
            group = ConditionGroup(
                conditions=[
                    ConditionSpec("username", Op.EQ, "john"),
                    ConditionSpec("is_active", Op.EQ, True),
                ],
                operator="AND",
            )
            clause = repo._build_group_clause(group)
            # Result: and_(UserTable.username == "john", UserTable.is_active == True)
            ```

            OR group:
            ```python
            group = ConditionGroup(
                conditions=[
                    ConditionSpec("username", Op.EQ, "john"),
                    ConditionSpec("email", Op.EQ, "john@ex.com"),
                ],
                operator="OR",
            )
            clause = repo._build_group_clause(group)
            # Result: or_(UserTable.username == "john", UserTable.email == "john@ex.com")
            ```

            NOT group:
            ```python
            group = ConditionGroup(
                conditions=[
                    ConditionSpec("username", Op.EQ, "john"),
                    ConditionSpec("is_active", Op.EQ, True),
                ],
                operator="AND",
                negated=True,
            )
            clause = repo._build_group_clause(group)
            # Result: not_(and_(UserTable.username == "john", UserTable.is_active == True))
            ```
        """
        if not group.conditions:
            return None

        clauses: list[sa.ColumnElement[bool]] = []

        for condition in group.conditions:
            if isinstance(condition, ConditionGroup):
                # Recursively handle nested group
                nested_clause = self._build_group_clause(condition)
                if nested_clause is not None:
                    clauses.append(nested_clause)
            else:
                # Handle single condition
                clause = self._condition_to_sqlalchemy(condition)
                clauses.append(clause)

        if not clauses:
            return None

        # Single clause, no need for and_/or_
        if len(clauses) == 1:
            result = clauses[0]
        else:
            # Combine with AND or OR
            result = sa.and_(*clauses) if group.operator == "AND" else sa.or_(*clauses)

        # Apply negation if needed
        if group.negated:
            return sa.not_(result)

        return result

    def build_order_by(self, filter: t.Optional[Filter]) -> list[sa.UnaryExpression[t.Any]]:  # noqa
        """Convert Filter sorts to SQLAlchemy order by clauses for
        SQLite.

        This method translates the filter sort specifications into SQLAlchemy
        order by expressions that can be used with SQLite queries.

        Args:
            filter: The filter to convert, or None for no sorting.

        Returns:
            A list of SQLAlchemy UnaryExpression objects for ORDER BY clauses.
            Returns empty list if filter is None or has no sorts.

        Examples:
            Single sort:
            ```python
            filter = user_filter().created_at.desc()
            order_clauses = repo.build_order_by(filter)
            # Result: [UserTable.created_at.desc()]
            ```

            Multiple sorts:
            ```python
            filter = (
                user_filter()
                .tier.desc()
                .created_at.asc()
                .username.asc()
            )
            order_clauses = repo.build_order_by(filter)
            # Result: [
            #     UserTable.tier.desc(),
            #     UserTable.created_at.asc(),
            #     UserTable.username.asc()
            # ]
            ```

            Using with SQLAlchemy:
            ```python
            order_clauses = repo.build_order_by(filter)
            stmt = sa.select(UserTable).order_by(*order_clauses)
            result = await session.execute(stmt)
            ```

        Notes:
            - Sort order is preserved as specified in the filter chain
            - SQLite applies sorts in the order they appear
            - Can be unpacked with * operator for order_by()
        """
        if filter is None or not filter._sorts:
            return []

        return [self._sort_to_sqlalchemy(sort) for sort in filter._sorts]

    def _get_column(self, field_name: str) -> sa.Column[t.Any]:
        """Get the SQLAlchemy column for a field name.

        Args:
            field_name: The name of the field.

        Returns:
            The SQLAlchemy Column object.

        Raises:
            AttributeError: If the field doesn't exist in the table.
        """
        if not hasattr(self.__table__, field_name):
            raise AttributeError(f"Table '{self.__table__.__name__}' has no field '{field_name}'")
        return getattr(self.__table__, field_name)  # type: ignore

    def _condition_to_sqlalchemy(self, condition: ConditionSpec) -> sa.ColumnElement[bool]:
        """Convert a single Condition to SQLAlchemy where clause for
        SQLite.

        Args:
            condition: The condition to convert.

        Returns:
            A SQLAlchemy ColumnElement expression for the WHERE clause.

        Raises:
            ValueError: If the operation is not supported.

        Examples:
            List operations:
            ```python
            # HAS: Check if JSON array contains a single element
            condition = ConditionSpec("tags", Op.HAS, "premium")
            result = repo._condition_to_sqlalchemy(condition)
            # Result: Uses SQLite JSON1 extension
            # SQL: WHERE json_extract(tags, '$') LIKE '%"premium"%'

            # CONTAINS: Check if JSON array contains all elements (subset check)
            condition = ConditionSpec(
                "tags", Op.CONTAINS, ["premium", "verified"]
            )
            result = repo._condition_to_sqlalchemy(condition)
            # Result: Multiple JSON checks combined with AND
            # SQL: WHERE json_extract(tags, '$') LIKE '%"premium"%'
            #       AND json_extract(tags, '$') LIKE '%"verified"%'
            ```

            String operations:
            ```python
            # String CONTAINS: Case-insensitive substring match
            condition = ConditionSpec("name", Op.CONTAINS, "john")
            result = repo._condition_to_sqlalchemy(condition)
            # Result: UserTable.name.like('%john%', escape='\\')
            # SQL: WHERE name LIKE '%john%'
            ```
        """
        column = self._get_column(condition.field)
        op = condition.op
        value = condition.value
        value2 = condition.value2

        match op:
            case Op.EQ:
                # Simple equality
                return column == value

            case Op.NE:
                # Not equal
                return column != value

            case Op.GT:
                # Greater than
                return column > value

            case Op.LT:
                # Less than
                return column < value

            case Op.GTE:
                # Greater than or equal to
                return column >= value

            case Op.LTE:
                # Less than or equal to
                return column <= value

            case Op.IN:
                # Value in list
                return column.in_(value)  # type: ignore

            case Op.NIN:
                # Value not in list
                return column.not_in(value)  # type: ignore

            case Op.BETWEEN:
                # BETWEEN is inclusive: field >= value1 AND field <= value2
                return sa.and_(column >= value, column <= value2)

            case Op.HAS:
                # For list fields (stored as JSON), check if single value exists in array
                # SQLite uses JSON1 extension for JSON operations
                # Use json_extract to get the full array, then use LIKE to check for the value
                # Format: WHERE json_extract(column, '$') LIKE '%"value"%'
                json_extract = sa.func.json_extract(column, "$")
                search_value = f'%"{value}"%'
                return json_extract.like(search_value)  # type: ignore

            case Op.CONTAINS:
                # Handle different field types for CONTAINS operation
                if isinstance(value, list):
                    # For list fields (stored as JSON): Check if database array contains ALL specified elements
                    # This is a subset check - database array must be a superset of the provided list
                    # SQLite doesn't have a native subset operator like PostgreSQL's @>
                    # We need to check each element individually using JSON1 extension
                    json_extract = sa.func.json_extract(column, "$")
                    clauses = []
                    for item in value:
                        search_value = f'%"{item}"%'
                        clauses.append(json_extract.like(search_value))  # type: ignore
                    # Combine all checks with AND
                    return sa.and_(*clauses)
                # For string fields, handle pattern matching
                pattern = str(value)

                # Check if it's a startswith/endswith pattern
                if pattern.startswith("^"):
                    # startswith: ^prefix -> prefix%
                    prefix = pattern[1:]  # Remove ^
                    # Escape SQL wildcards
                    escaped = prefix.replace("%", "\\%").replace("_", "\\_")
                    return column.like(f"{escaped}%", escape="\\")  # type: ignore

                if pattern.endswith("$"):
                    # endswith: suffix$ -> %suffix
                    suffix = pattern[:-1]  # Remove $
                    # Escape SQL wildcards
                    escaped = suffix.replace("%", "\\%").replace("_", "\\_")
                    return column.like(f"%{escaped}", escape="\\")  # type: ignore

                # Plain contains: case-insensitive substring match
                # For SQLite LIKE, we need to escape SQL wildcards (%, _)
                escaped = pattern.replace("%", "\\%").replace("_", "\\_")
                # SQLite LIKE is case-insensitive by default for ASCII characters
                return column.like(f"%{escaped}%", escape="\\")  # type: ignore

            case _:
                raise ValueError(f"Unsupported operation: {op}")

    def _sort_to_sqlalchemy(self, sort: SortSpec) -> sa.UnaryExpression[t.Any]:
        """Convert a single SortSpec to SQLAlchemy order by expression.

        Args:
            sort: The sort specification to convert.

        Returns:
            A SQLAlchemy UnaryExpression for ORDER BY clause.

        Examples:
            ```python
            # Ascending sort
            sort = SortSpec("username", Order.ASC)
            expr = repo._sort_to_sqlalchemy(sort)
            # Result: UserTable.username.asc()

            # Descending sort
            sort = SortSpec("created_at", Order.DESC)
            expr = repo._sort_to_sqlalchemy(sort)
            # Result: UserTable.created_at.desc()
            ```
        """
        column = self._get_column(sort.field)

        if sort.order == Order.ASC:
            return column.asc()
        return column.desc()
