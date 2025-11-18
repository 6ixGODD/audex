from __future__ import annotations

import abc
import contextlib
import functools as ft
import inspect
import time
import traceback as tb
import typing as t

from audex.helper.mixin import ContextMixin
from audex.logger.types import LoggingTarget
from audex.logger.types import Loglevel

P = t.ParamSpec("P")
R = t.TypeVar("R")

INCLUDE_LOCATION = "__include_location__"


@t.runtime_checkable
class Logger(t.Protocol):
    """Protocol defining the logger interface."""

    def with_context(self, /, **kwargs: t.Any) -> Logger: ...
    def with_tag(self, tag: str, /) -> Logger: ...
    def with_request_id(self, request_id: str, /) -> Logger: ...
    def with_user_id(self, user_id: str, /) -> Logger: ...
    def log(self, msg: str, /, level: Loglevel, **kwargs: t.Any) -> None: ...
    def debug(self, msg: str, /, **kwargs: t.Any) -> None: ...
    def info(self, msg: str, /, **kwargs: t.Any) -> None: ...
    def warning(self, msg: str, /, **kwargs: t.Any) -> None: ...
    def error(self, msg: str, /, **kwargs: t.Any) -> None: ...
    def critical(self, msg: str, /, **kwargs: t.Any) -> None: ...
    @contextlib.contextmanager
    def catch(
        self,
        msg: str,
        /,
        exc: type[BaseException] | tuple[type[BaseException], ...] = Exception,
        excl_exc: type[BaseException] | tuple[type[BaseException], ...] = (),
    ) -> t.Generator[None, None, None]: ...
    @property
    def targets(self) -> list[LoggingTarget]: ...
    def sync(self) -> None: ...
    def close(self) -> None: ...


class LoggerBackend(abc.ABC):
    """Abstract base class for logger backend implementations."""

    @abc.abstractmethod
    def setup_handlers(self, targets: list[LoggingTarget]) -> None:
        """Setup logging handlers for the specified targets."""

    @abc.abstractmethod
    def log(self, msg: str, /, level: Loglevel, **ctx: t.Any) -> None:
        """Log a message at the specified level with context."""

    @abc.abstractmethod
    def sync(self) -> None:
        """Flush any buffered log messages."""

    @abc.abstractmethod
    def close(self) -> None:
        """Close the logger and cleanup resources."""


class ContextualLogger(Logger, ContextMixin):
    """Logger implementation with support for contextual information.

    Performance optimizations:
    - Lazy context merging (only when actually logging)
    - Minimal dictionary copying
    - Cached app context extraction
    """

    __slots__ = ("_app_context", "_app_context_cache", "_backend", "_context", "_targets")

    def __init__(
        self,
        backend: LoggerBackend,
        targets: t.Sequence[LoggingTarget] | None = None,
        extra_context: dict[str, t.Any] | None = None,
    ):
        self._backend = backend
        self._context = extra_context or {}
        self._targets = list(targets or [])
        self._backend.setup_handlers(self._targets)

    def with_context(self, /, **kwargs: t.Any) -> ContextualLogger:
        """Create a new logger with additional context."""
        new_context = ContextualLogger(self._backend, self._targets)
        # combine existing context with new context
        new_context._context = {**self._context, **kwargs} if self._context else kwargs
        return new_context

    def with_tag(self, tag: str, /) -> ContextualLogger:
        """Create a new logger with a tag."""
        return self.with_context(TAG=tag)

    def _merge_contexts(self, **kwargs: t.Any) -> dict[str, t.Any]:
        """Merge all context sources in priority order."""
        return {**self._context, **kwargs}

    def log(self, msg: str, /, level: Loglevel, **kwargs: t.Any) -> None:
        """Log a message at the specified level."""
        ctx = self._merge_contexts(**kwargs)
        self._backend.log(msg, level, **ctx)

    def debug(self, msg: str, /, **kwargs: t.Any) -> None:
        """Log a debug message."""
        return self.log(msg, level=Loglevel.DEBUG, **kwargs)

    def info(self, msg: str, /, **kwargs: t.Any) -> None:
        """Log an info message."""
        return self.log(msg, level=Loglevel.INFO, **kwargs)

    def warning(self, msg: str, /, **kwargs: t.Any) -> None:
        """Log a warning message."""
        return self.log(msg, level=Loglevel.WARNING, **kwargs)

    def error(self, msg: str, /, **kwargs: t.Any) -> None:
        """Log an error message."""
        return self.log(msg, level=Loglevel.ERROR, **kwargs)

    def critical(self, msg: str, /, **kwargs: t.Any) -> None:
        """Log a critical message."""
        return self.log(msg, level=Loglevel.CRITICAL, **kwargs)

    @contextlib.contextmanager
    def catch(
        self,
        msg: str,
        /,
        exc: type[BaseException] | tuple[type[BaseException], ...] = Exception,
        excl_exc: type[BaseException] | tuple[type[BaseException], ...] = (),
    ) -> t.Generator[None, None, None]:
        """Context manager for catching and logging exceptions."""
        try:
            yield
        except exc as e:
            if isinstance(e, excl_exc):
                raise
            self.error(
                f"{msg}: {e}",
                exception_type=type(e).__name__,
                exception=str(e),
                traceback=tb.format_exc(),
            )
            raise

    @property
    def targets(self) -> list[LoggingTarget]:
        """Get the list of logging targets."""
        return self._targets

    def sync(self) -> None:
        """Flush any buffered log messages."""
        self._backend.sync()

    def close(self) -> None:
        """Close the logger and cleanup resources."""
        self._backend.close()

    def __repr__(self) -> str:
        return f"CONTEXTUAL LOGGER <{self.__class__.__name__}(targets={len(self._targets)})>"


def log_method(
    msg: str | None = None,
    level: Loglevel = "info",
    *,
    exc: type[BaseException] | tuple[type[BaseException], ...] = Exception,
    excl_exc: type[BaseException] | tuple[type[BaseException], ...] = (),
    logargs: bool = False,
    logres: bool = False,
    logdur: bool = True,
    success_level: Loglevel = "info",
    error_level: Loglevel = "error",
    pre_exec: bool = True,
    post_exec: bool = True,
) -> t.Callable[[t.Callable[P, R]], t.Callable[P, R]]:
    """Decorator for automatic method execution logging.

    This decorator automatically adds location context (module, function, class,
    line) to all logs generated within its scope.

    Args:
        msg: Optional custom message to log.
        level: Log level for pre-execution log.
        exc: Exception types to catch and log.
        excl_exc: Exception types to exclude from logging.
        logargs: Whether to log function arguments.
        logres: Whether to log function result.
        logdur: Whether to log execution duration.
        success_level: Log level for successful execution.
        error_level: Log level for errors.
        pre_exec: Whether to log before execution.
        post_exec: Whether to log after execution.

    Returns:
        Decorated function with logging.
    """

    def decorator(fn: t.Callable[P, R]) -> t.Callable[P, R]:
        # Extract function metadata
        func_name = fn.__name__
        module_name = getattr(fn, "__module__", "unknown")

        # Try to get source line number
        try:
            source_line = inspect.getsourcelines(fn)[1]
        except (OSError, TypeError):
            source_line = 0

        @ft.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Try to get logger from first argument
            logger: Logger | None = None
            if args and hasattr(args[0], "logger"):
                logger = args[0].logger

            if logger is None or not isinstance(logger, Logger):
                # No logger available, just execute the function
                return fn(*args, **kwargs)

            # Build full function name with class if available
            class_name = None
            if args and hasattr(args[0], "__class__"):
                class_name = args[0].__class__.__name__
                full_name = f"{class_name}.{func_name}"
            else:
                full_name = func_name

            # Location context
            location_ctx = {
                "function": func_name,
                "module": module_name,
                "full_name": full_name,
                "line": source_line,
                INCLUDE_LOCATION: True,
            }

            if class_name:
                location_ctx["class"] = class_name

            # log arguments if enabled
            if logargs:
                sig = inspect.signature(fn)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                filtered_args = {
                    k: v for k, v in bound_args.arguments.items() if k not in ("self", "cls")
                }
                location_ctx["arguments"] = filtered_args

            start_time = time.time()

            if pre_exec:
                pre_msg = msg or f"Executing {full_name}"
                logger.log(pre_msg, level=level, **location_ctx, execution_stage="pre")

            try:
                result = fn(*args, **kwargs)

                if post_exec:
                    end_time = time.time()
                    duration = end_time - start_time

                    success_context = location_ctx.copy()

                    if logdur:
                        success_context["duration_ms"] = round(duration * 1000, 2)

                    if logres:
                        if hasattr(result, "__dict__"):
                            success_context["result"] = str(result)
                        elif isinstance(result, (str | int | float | bool | list | dict)):
                            success_context["result"] = result
                        else:
                            success_context["result"] = str(result)

                    success_msg = msg or f"Completed {full_name}"
                    logger.log(
                        success_msg,
                        level=success_level,
                        **success_context,
                        execution_stage="post",
                        status="success",
                    )

                return result

            except exc as e:
                if isinstance(e, excl_exc):
                    raise

                end_time = time.time()
                duration = end_time - start_time

                error_context = location_ctx.copy()
                error_context.update({
                    "exception_type": type(e).__name__,
                    "exception": str(e),
                    "traceback": tb.format_exc(),
                    "execution_stage": "error",
                    "status": "error",
                })

                if logdur:
                    error_context["duration_ms"] = round(duration * 1000, 2)

                error_msg = msg or f"Failed {full_name}: {e}"
                logger.log(error_msg, level=error_level, **error_context)

                raise

        return wrapper

    return decorator
