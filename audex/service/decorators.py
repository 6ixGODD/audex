from __future__ import annotations

import functools as ft
import typing as t

if t.TYPE_CHECKING:
    from audex.service import BaseService

    ServiceMethodT = t.TypeVar("ServiceMethodT", bound=t.Callable[..., t.Awaitable[t.Any]])


def require_auth(func: ServiceMethodT) -> ServiceMethodT:
    """Decorator to require authentication for service methods.

    This decorator checks if the user is authenticated before allowing
    access to the decorated service method. If the user is not authenticated,
    an exception is raised.

    Args:
        func: The service method to decorate.

    Returns:
        The decorated service method with authentication check.
    """

    @ft.wraps(func)
    async def wrapper(self: BaseService, *args: t.Any, **kwargs: t.Any) -> t.Any:
        if await self.session.is_logged_in():
            return await func(self, *args, **kwargs)
        raise PermissionError("Authentication required to access this method.")

    return wrapper


def log_call(func: ServiceMethodT) -> ServiceMethodT:
    """Decorator to log calls to service methods.

    This decorator logs the invocation of the decorated service method,
    including its name and arguments.

    Args:
        func: The service method to decorate.

    Returns:
        The decorated service method with logging.
    """

    @ft.wraps(func)
    async def wrapper(self: BaseService, *args: t.Any, **kwargs: t.Any) -> t.Any:
        op = func.__name__
        msg = f"Calling {op} with args={args} kwargs={kwargs}"
        if doc_id := self.session.get_doctor_id():
            msg += f" [Doctor ID: {doc_id}]"

        self.logger.info(msg)
        try:
            result = await func(self, *args, **kwargs)
            self.logger.info(f"{op} completed successfully.")
            return result
        except Exception as e:
            self.logger.error(f"{op} failed with error: {e}")
            raise

    return wrapper
