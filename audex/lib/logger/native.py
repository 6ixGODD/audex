from __future__ import annotations

import json
import logging
import logging.handlers
import pathlib as p
import sys
import typing as t

from audex import utils
from audex.logger import INCLUDE_LOCATION
from audex.logger import LoggerBackend
from audex.logger.schema import CodeLocationInfo
from audex.logger.schema import ExceptionInfo
from audex.logger.schema import format_log_record
from audex.logger.types import LoggingTarget
from audex.logger.types import Loglevel

LEVEL_MAPPING = {
    Loglevel.DEBUG: logging.DEBUG,
    Loglevel.INFO: logging.INFO,
    Loglevel.WARNING: logging.WARNING,
    Loglevel.ERROR: logging.ERROR,
    Loglevel.CRITICAL: logging.CRITICAL,
}
EXCLUDED_CONTEXT_KEYS = frozenset({
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "getMessage",
    "exc_info",
    "exc_text",
    "stack_info",
    "message",
    INCLUDE_LOCATION,
})


class ContextFormatter(logging.Formatter):
    """Enhanced formatter with ANSI colors and improved layout."""

    LEVEL_COLORS: t.ClassVar[
        dict[
            int,
            tuple[
                utils.ANSI.FG | utils.ANSI.BG | utils.ANSI.STYLE,
                ...,
            ],
        ]
    ] = {
        logging.DEBUG: (
            utils.ANSI.FG.GRAY,
            utils.ANSI.STYLE.DIM,
        ),
        logging.INFO: (utils.ANSI.FG.BRIGHT_CYAN,),
        logging.WARNING: (
            utils.ANSI.FG.BRIGHT_YELLOW,
            utils.ANSI.STYLE.BOLD,
        ),
        logging.ERROR: (
            utils.ANSI.FG.BRIGHT_RED,
            utils.ANSI.STYLE.BOLD,
        ),
        logging.CRITICAL: (
            utils.ANSI.FG.BRIGHT_RED,
            utils.ANSI.BG.WHITE,
            utils.ANSI.STYLE.BOLD,
        ),
    }

    COMPONENT_STYLES: t.ClassVar[
        dict[
            str,
            tuple[
                utils.ANSI.FG | utils.ANSI.BG | utils.ANSI.STYLE,
                ...,
            ],
        ]
    ] = {
        "timestamp": (utils.ANSI.FG.GRAY,),
        "logger": (utils.ANSI.FG.MAGENTA,),
        "tag": (utils.ANSI.FG.CYAN, utils.ANSI.STYLE.BOLD),
        "arrow": (utils.ANSI.FG.GRAY,),
        "context": (utils.ANSI.FG.GRAY,),
    }

    def __init__(self, is_console: bool = False, use_colors: bool = True):
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")
        self.is_console = is_console
        self.use_colors = use_colors and utils.ANSI.supports_color()
        if self.use_colors:
            utils.ANSI.enable(True)

    @staticmethod
    def _extract_context(record: logging.LogRecord) -> dict[str, t.Any]:
        """Extract context from log record, excluding standard
        fields."""
        context = {}
        for key, value in record.__dict__.items():
            if not key.startswith("_") and key not in EXCLUDED_CONTEXT_KEYS:
                try:
                    json.dumps(value)
                    context[key] = value
                except (TypeError, ValueError):
                    context[key] = str(value)
        return context

    def _format_logger_with_tag(self, name: str, context: dict[str, t.Any]) -> str:
        """Format logger name with optional TAG."""
        tag = context.get("TAG")

        if tag:
            available_space = 39
            name_len = len(name)
            tag_len = len(tag)
            total_needed = name_len + tag_len

            if total_needed <= available_space:
                truncated_name = name
                truncated_tag = tag
            elif name_len <= 8:
                truncated_name = name
                remaining = available_space - name_len
                truncated_tag = f"...{tag[-(remaining - 3) :]}" if tag_len > remaining else tag
            else:
                max_tag_space = min(tag_len, 8)
                max_name_space = available_space - max_tag_space

                if name_len > max_name_space:
                    truncated_name = f"...{name[-(max_name_space - 3) :]}"
                else:
                    truncated_name = name
                    max_tag_space = available_space - len(truncated_name)

                if tag_len > max_tag_space:
                    truncated_tag = f"...{tag[-(max_tag_space - 3) :]}"
                else:
                    truncated_tag = tag

            full_display = f"{truncated_name}.{truncated_tag}"

            if self.use_colors:
                colored_name = utils.ANSI.format(truncated_name, *self.COMPONENT_STYLES["logger"])
                colored_tag = utils.ANSI.format(truncated_tag, *self.COMPONENT_STYLES["tag"])
                colored_dot = utils.ANSI.format(".", utils.ANSI.FG.GRAY)
                display = f"{colored_name}{colored_dot}{colored_tag}"
            else:
                display = full_display

            if len(full_display) < 40:
                display += " " * (40 - len(full_display))
            else:
                display = display[:40] if not self.use_colors else display
        else:
            truncated_name = f"...{name[-37:]}" if len(name) > 40 else name
            display = f"{truncated_name:<40}"

            if self.use_colors:
                display = utils.ANSI.format(display, *self.COMPONENT_STYLES["logger"])

        return display

    def _format_context(self, context: dict[str, t.Any], prefix_len: int) -> str:
        """Format context for console output."""
        ctx = {k: v for k, v in context.items() if k != "TAG"}
        if not ctx:
            return ""

        indent = " " * (prefix_len - 3)
        arrow = "==>"
        if self.use_colors:
            arrow = utils.ANSI.format(arrow, *self.COMPONENT_STYLES["context"])

        lines = []
        for k, v in ctx.items():
            line = f"{k}={v}"
            if self.use_colors:
                line = utils.ANSI.format(line, *self.COMPONENT_STYLES["context"])
            lines.append(f"\n{indent}{arrow} {line}")

        return "".join(lines)

    @staticmethod
    def _get_prefix_length(timestamp: str, logger: str, loglevel: str) -> int:
        """Calculate prefix length for alignment."""
        return len(f"[{timestamp}] [{logger}] [{loglevel}] => ")

    def format(self, record: logging.LogRecord) -> str:
        context = self._extract_context(record)

        if self.is_console:
            return self._format_console(record, context)
        return self._format_json(record, context)

    def _format_console(self, record: logging.LogRecord, context: dict[str, t.Any]) -> str:
        """Format for console output with colors and alignment."""
        timestamp = self.formatTime(record, self.datefmt)
        logger_name = self._format_logger_with_tag(record.name, context)
        level_name = f"{record.levelname:<8}"
        message = record.getMessage()

        if self.use_colors:
            timestamp = utils.ANSI.format(timestamp, *self.COMPONENT_STYLES["timestamp"])
            level_name = utils.ANSI.format(level_name, *self.LEVEL_COLORS.get(record.levelno, ()))
            arrow = utils.ANSI.format("=>", *self.COMPONENT_STYLES["arrow"])
        else:
            arrow = "=>"

        plain_timestamp = self.formatTime(record, self.datefmt)
        plain_level = f"{record.levelname:<8}"
        prefix_len = self._get_prefix_length(
            plain_timestamp,
            "somnmind" + 32 * " ",
            plain_level,
        )
        indent = " " * (prefix_len - 3)

        if "\n" in message:
            lines = message.split("\n")
            message_lines = [lines[0]]
            for line in lines[1:]:
                message_lines.append(f"{indent}{arrow} {line}")
            message = "\n".join(message_lines)

        log_line = f"[{timestamp}] [{logger_name}] [{level_name}] {arrow} {message}"

        context_str = self._format_context(context, prefix_len)
        if context_str:
            log_line += context_str

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            if not log_line.endswith("\n"):
                log_line += "\n"

            exc_lines = [line for line in record.exc_text.split("\n") if line.strip()]
            for line in exc_lines:
                colored_line = line
                if self.use_colors:
                    colored_line = utils.ANSI.format(line, utils.ANSI.FG.RED, utils.ANSI.STYLE.DIM)
                log_line += f"{indent}{arrow} {colored_line}\n"

        return log_line.rstrip("\n")

    def _format_json(self, record: logging.LogRecord, context: dict[str, t.Any]) -> str:
        """Format for file output as JSON using standard schema."""
        timestamp = self.formatTime(record, self.datefmt)

        # 只有当标记 _INCLUDE_LOCATION_KEY 存在时才包含 location
        location: CodeLocationInfo | None = None
        include_location = getattr(record, INCLUDE_LOCATION, False)

        if include_location:
            location = CodeLocationInfo(
                module=context.get("module", record.module),
                function=context.get("function", record.funcName),
                line=context.get("line", record.lineno),
                process=record.process,
                thread=record.thread,
            )

        # Build exception info if present
        exception_info: ExceptionInfo | None = None
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            exception_info = ExceptionInfo(
                exception_type=exc_type.__name__ if exc_type else "Unknown",
                exception=str(exc_value) if exc_value else "",
                traceback=self.formatException(record.exc_info),
            )

        # 从 context 中排除 location 相关字段
        clean_context = {
            k: v
            for k, v in context.items()
            if k not in ("module", "function", "line", "full_name", "class")
        }

        # Use format_log_record to create structured log
        log_data = format_log_record(
            timestamp=timestamp,
            level=record.levelname,
            message=record.getMessage(),
            logger=record.name,
            location=location,
            exception=exception_info,
            context=clean_context if clean_context else None,
        )

        return json.dumps(log_data, ensure_ascii=False, separators=(",", ":"))


def _create_handler(target: LoggingTarget) -> logging.Handler:
    """Create appropriate handler based on target configuration."""
    if target.logname in ("stdout", "stderr"):
        stream = sys.stdout if target.logname == "stdout" else sys.stderr
        handler = logging.StreamHandler(stream)
        formatter = ContextFormatter(is_console=True, use_colors=True)
    else:
        file_path = p.Path(target.logname)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if target.rotation:
            if target.rotation.size_based:
                max_bytes = target.rotation.size_based.max_size * 1024 * 1024
                handler = logging.handlers.RotatingFileHandler(
                    filename=str(file_path),
                    maxBytes=max_bytes,
                    backupCount=target.rotation.size_based.backup_count,
                    encoding="utf-8",
                )
            elif target.rotation.time_based:
                handler = logging.handlers.TimedRotatingFileHandler(
                    filename=str(file_path),
                    when="H",
                    interval=target.rotation.time_based.interval,
                    backupCount=target.rotation.time_based.backup_count,
                    encoding="utf-8",
                )
            else:
                handler = logging.FileHandler(filename=str(file_path), encoding="utf-8")
        else:
            handler = logging.FileHandler(filename=str(file_path), encoding="utf-8")

        formatter = ContextFormatter(is_console=False, use_colors=False)

    handler.setFormatter(formatter)
    handler.setLevel(LEVEL_MAPPING.get(target.loglevel, logging.INFO))
    return handler


class NativeLoggingBackend(LoggerBackend):
    """Native logging backend with enhanced formatting."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("somnmind")
        self.logger.setLevel(logging.DEBUG)
        self._handlers: list[logging.Handler] = []
        self._is_setup = False
        utils.ANSI.enable(utils.ANSI.supports_color())

    def setup_handlers(self, targets: list[LoggingTarget]) -> None:
        if self._is_setup:
            return

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        self._handlers.clear()

        for target in targets:
            handler = _create_handler(target)
            self.logger.addHandler(handler)
            self._handlers.append(handler)

        self.logger.propagate = False
        self._is_setup = True

    def log(self, msg: str, /, level: Loglevel, **context: t.Any) -> None:
        """Log a message with context."""
        log_level = LEVEL_MAPPING.get(level, logging.INFO)

        self.logger._log(
            log_level,
            msg,
            args=(),
            exc_info=None,
            extra=context,
            stack_info=False,
            stacklevel=3,
        )

    def sync(self) -> None:
        """Flush all handlers."""
        for handler in self._handlers:
            if hasattr(handler, "flush"):
                handler.flush()

    def close(self) -> None:
        """Close all handlers."""
        for handler in self._handlers:
            try:
                handler.close()
                self.logger.removeHandler(handler)
            except Exception:
                pass
        self._handlers.clear()
        self._is_setup = False
