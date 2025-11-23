from __future__ import annotations

import abc
import builtins
import inspect
import typing as t

from audex.entity import BaseEntity
from audex.filters import Filter

E = t.TypeVar("E", bound=BaseEntity)


class RepositoryMeta(abc.ABCMeta):
    """Metaclass that automatically applies decorators to repository
    methods.

    Supports configuration via class inheritance:

    Example:
        ```python
        # Enable logging (default)
        class UserRepository(MongoRepository[User]):
            pass


        # Disable logging
        class UserRepository(MongoRepository[User], log=False):
            pass
        ```
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        log: bool = True,
        **kwargs: t.Any,
    ) -> type:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Skip decoration for abstract base classes
        if abc.ABC in bases:
            return cls

        # Check if this is a concrete repository (inherits from BaseRepository)
        is_repository = any(
            isinstance(base, RepositoryMeta) and hasattr(base, "__repotype__") for base in bases
        )

        if not is_repository:
            return cls

        # Skip if log is disabled
        if not log:
            return cls

        # Import decorator only when needed
        from audex.lib.repos.decorators import log_repo_call

        # Get all public methods (not starting with _)
        for attr_name in dir(cls):
            # Skip private/protected methods
            if attr_name.startswith("_"):
                continue

            attr = getattr(cls, attr_name)

            # Skip if not a method
            if not inspect.ismethod(attr) and not inspect.isfunction(attr):
                continue

            attr: t.Callable[[t.Concatenate[cls, ...]], t.Awaitable[t.Any]]

            # Skip if already decorated (has marker attribute)
            if hasattr(attr, "_repo_decorated"):
                continue

            # Skip properties, classmethods, staticmethods
            if isinstance(
                inspect.getattr_static(cls, attr_name), (property | classmethod | staticmethod)
            ):
                continue

            # Apply log decorator
            decorated = log_repo_call(attr)

            # Mark as decorated to avoid double decoration
            decorated._repo_decorated = True

            # Replace the method
            setattr(cls, attr_name, decorated)

        return cls


class BaseRepository(abc.ABC, t.Generic[E], metaclass=RepositoryMeta):
    """Abstract base repository for generic CRUD operations.

    This class defines the standard CRUD interface that all repositories
    must implement, regardless of the underlying database technology.
    """

    __repotype__: t.ClassVar[str]  # e.g., "mongodb", "postgresql", "sqlite"

    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "__repotype__"):
            raise NotImplementedError(
                f"Subclass {cls.__name__} must define __repotype__ class variable"
            )

    @abc.abstractmethod
    async def create(self, data: E, /) -> str: ...
    @abc.abstractmethod
    async def read(self, id: str, /) -> E | None: ...
    @abc.abstractmethod
    async def first(self, filter: Filter) -> E | None: ...
    @abc.abstractmethod
    async def list(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
        *,
        page_index: int = 0,
        page_size: int = 100,
    ) -> builtins.list[E]: ...
    @abc.abstractmethod
    async def update(self, data: E, /) -> str: ...
    @abc.abstractmethod
    async def update_many(self, datas: builtins.list[E]) -> builtins.list[str]: ...
    @abc.abstractmethod
    async def delete(self, id: str, /) -> bool: ...
    @abc.abstractmethod
    async def delete_many(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
    ) -> builtins.list[str]: ...
    @abc.abstractmethod
    async def count(self, filter: t.Optional[Filter] = None) -> int: ...  # noqa

    async def exists(self, filter: Filter) -> bool:
        count = await self.count(filter)
        return count > 0

    def __repr__(self) -> str:
        return f"REPOSITORY <{self.__class__.__name__}>"
