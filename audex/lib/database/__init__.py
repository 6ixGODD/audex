from __future__ import annotations

import abc
import typing as t

from audex.helper.mixin import AsyncContextMixin


class Database(AsyncContextMixin, abc.ABC):
    """Abstract base class for database containers.

    All database implementations should inherit from this class and implement
    the required abstract methods. This ensures a consistent interface across
    different database backends.

    The class provides:
    1. Lifecycle management through AsyncContextMixin (init/close)
    2. Health check interface (ping)
    3. Raw query execution interface (exec)

    Example:
        ```python
        class MyDatabase(Database):
            async def init(self) -> None:
                # Initialize connection
                pass

            async def close(self) -> None:
                # Close connection
                pass

            async def ping(self) -> bool:
                # Check connectivity
                pass

            async def exec(
                self, readonly: bool, **kwargs: t.Any
            ) -> t.Any:
                # Execute raw query
                pass
        ```
    """

    @abc.abstractmethod
    async def ping(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is reachable and healthy, False otherwise.

        Note:
            Implementations should not raise exceptions. Instead, catch
            any errors and return False.
        """
        pass

    @abc.abstractmethod
    async def exec(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        """Execute a raw database command.

        This method provides a way to execute native database commands
        when ORM abstractions are insufficient or when optimization
        requires direct database access.

        Args:
            *args: Positional arguments for the database command.
            **kwargs: Database-specific command parameters.

        Returns:
            Database-specific result object.

        Raises:
            RuntimeError: If the execution fails.

        Note:
            The exact signature and return type will vary by database
            implementation. Refer to specific database class documentation
            for details.
        """
        pass

    def __repr__(self) -> str:
        return f"DATABASE <{self.__class__.__name__}>"
