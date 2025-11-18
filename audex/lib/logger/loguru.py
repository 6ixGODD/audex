from __future__ import annotations

import contextlib
import datetime
import json
import os
import sys
import traceback
import typing as t

from audex.logger import LoggerBackend
from audex.logger.schema import CodeLocationInfo
from audex.logger.schema import ExceptionInfo
from audex.logger.schema import format_log_record
from audex.logger.types import LoggingTarget
from audex.logger.types import Loglevel
from audex.logger.types import Rotation

try:
    from loguru import _file_sink
    from loguru import logger

    if t.TYPE_CHECKING:
        from loguru import Message

except ImportError as e:
    raise ImportError(
        "loguru is required for LoguruBackend. Please install it via 'pip install loguru'."
    ) from e

LEVEL_MAPPING = {
    Loglevel.DEBUG: "DEBUG",
    Loglevel.INFO: "INFO",
    Loglevel.WARNING: "WARNING",
    Loglevel.ERROR: "ERROR",
    Loglevel.CRITICAL: "CRITICAL",
}


@t.overload
def _fetch_loguru_rotation(rotation: None) -> tuple[None, None]: ...
@t.overload
def _fetch_loguru_rotation(rotation: Rotation) -> tuple[datetime.timedelta | str, int | None]: ...
def _fetch_loguru_rotation(
    rotation: Rotation | None,
) -> tuple[datetime.timedelta | str | None, int | None]:
    if rotation is None:
        return None, None

    if rotation.size_based:
        return f"{rotation.size_based.max_size} MB", rotation.size_based.backup_count
    if rotation.time_based:
        return datetime.timedelta(
            hours=rotation.time_based.interval
        ), rotation.time_based.backup_count
    return None, None


class JsonSink:
    """Wrapper around loguru's FileSink that outputs structured JSON."""

    def __init__(
        self,
        path: os.PathLike[str],
        *,
        rotation: str | int | datetime.time | datetime.timedelta | None = None,
        retention: str | int | datetime.timedelta | None = None,
        encoding: str = "utf-8",
    ):
        # Use loguru's built-in FileSink for rotation support
        self._file_sink = _file_sink.FileSink(
            path,
            rotation=rotation,
            retention=retention,
            compression=None,
            delay=False,
            mode="a",
            buffering=1,
            encoding=encoding,
            errors=None,
            newline=None,
        )

    def write(self, message: Message) -> None:
        """Convert to structured JSON and write."""
        record = message.record
        extra = record["extra"]

        # Build location info - prioritize context (from decorator/manual), fallback to record
        location = CodeLocationInfo(
            module=extra.get("ctx_module") or extra.get("module", record["module"]),
            function=extra.get("ctx_function") or extra.get("function", record["function"]),
            line=extra.get("ctx_line") or extra.get("line", record["line"]),
            process=record["process"].id,
            thread=record["thread"].id,
        )

        # Build exception info if present
        exception_info: ExceptionInfo | None = None
        if exc_record := record["exception"]:
            exception_info = ExceptionInfo(
                exception_type=exc_record.type.__name__ if exc_record.type else "Unknown",
                exception=str(exc_record.value) if exc_record.value else "",
                traceback="".join(
                    traceback.format_exception(
                        exc_record.type, exc_record.value, exc_record.traceback
                    )
                )
                if exc_record.traceback
                else "",
            )

        # Filter out location fields from context to avoid duplication
        clean_context = {k: v for k, v in extra.items() if k not in {"module", "function", "line"}}

        # Use format_log_record to create structured log
        log_data = format_log_record(
            timestamp=record["time"].strftime("%Y-%m-%d %H:%M:%S"),
            level=record["level"].name,
            message=record["message"],
            logger=record["name"],
            location=location,
            exception=exception_info,
            context=clean_context if clean_context else None,
        )

        json_line = json.dumps(log_data, ensure_ascii=False, separators=(",", ":"))
        self._file_sink.write(json_line + "\n")

    def stop(self) -> None:
        """Stop the sink."""
        if hasattr(self._file_sink, "stop"):
            self._file_sink.stop()


class LoguruBackend(LoggerBackend):
    def __init__(self) -> None:
        self.logger = logger
        self.logger.remove()
        self.handler_ids: list[int] = []
        self.sinks: list[JsonSink] = []
        self.is_setup = False

    def setup_handlers(self, targets: list[LoggingTarget]) -> None:
        if self.is_setup:
            return

        for target in targets:
            rotation, retention = _fetch_loguru_rotation(target.rotation)
            level = target.loglevel

            if target.logname == "stdout":
                handler_id = self.logger.add(
                    sys.stdout,
                    level=LEVEL_MAPPING.get(level, "INFO"),
                    colorize=True,
                    serialize=False,
                    backtrace=False,
                    diagnose=False,
                    catch=False,
                )
                self.handler_ids.append(handler_id)
            elif target.logname == "stderr":
                handler_id = self.logger.add(
                    sys.stderr,
                    level=LEVEL_MAPPING.get(level, "ERROR"),
                    colorize=True,
                    serialize=False,
                    backtrace=False,
                    diagnose=False,
                    catch=False,
                )
                self.handler_ids.append(handler_id)
            else:
                # Use structured JSON sink with rotation support
                sink = JsonSink(
                    target.logname,
                    rotation=rotation,
                    retention=retention,
                    encoding="utf-8",
                )
                self.sinks.append(sink)

                handler_id = self.logger.add(
                    sink,
                    level=LEVEL_MAPPING.get(level, "INFO"),
                    colorize=False,
                    serialize=False,
                    backtrace=False,
                    diagnose=False,
                    catch=False,
                )
                self.handler_ids.append(handler_id)

        self.is_setup = True

    def log(self, msg: str, /, level: Loglevel, **context: t.Any) -> None:
        self.logger.bind(**context).log(LEVEL_MAPPING.get(level, "INFO"), msg)

    def sync(self) -> None:
        pass  # do nothing, loguru is synchronous

    def close(self) -> None:
        for handler_id in self.handler_ids:
            with contextlib.suppress(ValueError):
                self.logger.remove(handler_id)
        self.handler_ids.clear()

        for sink in self.sinks:
            sink.stop()
        self.sinks.clear()

        self.is_setup = False
