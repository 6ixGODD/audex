from __future__ import annotations

import functools as ft
import typing as t

if t.TYPE_CHECKING:
    from audex.lib.repos import BaseRepository

    RepositoryMethodT = t.TypeVar("RepositoryMethodT", bound=t.Callable[..., t.Awaitable[t.Any]])


def log_repo_call(func: RepositoryMethodT) -> RepositoryMethodT:
    """Decorator to log repository method calls.

    Logs the operation with repo type, collection/table name, and operation
    name. This decorator should be applied BEFORE track_repo_call decorator.

    Example:
        ```python
        class UserRepository(MongoRepository[User]):
            @log_repo_call
            @track_repo_call
            async def create(self, data: User) -> str:
                # Implementation
                return user_id
        ```
    """

    @ft.wraps(func)
    async def wrapper(self: BaseRepository[t.Any], *args: t.Any, **kwargs: t.Any) -> t.Any:
        operation = func.__name__
        repo_type = self.__repotype__

        # Get collection name from subclass
        if hasattr(self, "__collname__"):
            collection = self.__collname__
        elif hasattr(self, "__tablename__"):
            collection = self.__tablename__
        else:
            collection = "unknown"

        # Log the call
        self.logger.info(  # type: ignore
            f"Repository operation: {repo_type}.{collection}.{operation}",
            repo_type=repo_type,
            collection=collection,
            operation=operation,
        )

        try:
            result = await func(self, *args, **kwargs)

            self.logger.info(  # type: ignore
                f"Repository operation completed: {repo_type}.{collection}.{operation}",
                repo_type=repo_type,
                collection=collection,
                operation=operation,
                status="success",
            )
            return result

        except Exception as e:
            self.logger.error(  # type: ignore
                f"Repository operation failed: {repo_type}.{collection}.{operation}: {e}",
                repo_type=repo_type,
                collection=collection,
                operation=operation,
                error=str(e),
                error_type=type(e).__name__,
                status="error",
            )
            raise

    return wrapper  # type: ignore
