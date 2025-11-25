from __future__ import annotations

import json
import os
import sys
import typing as t

from pydantic import Field
from pydantic import model_validator

from audex.helper.mixin import ContextMixin
from audex.helper.settings import BaseModel


class SizeBasedRotation(BaseModel):
    max_size: int = Field(
        default=10,
        description="Maximum size (MB) of the log file before rotation",
        ge=1,
        le=1024 * 1024,
    )

    backup_count: int = Field(
        default=5,
        description="Number of backup files to keep",
        ge=0,
        le=100,
    )


class TimeBasedRotation(BaseModel):
    interval: int = Field(
        default=1,
        description="Interval in hours for log rotation",
        ge=1,
        le=24,
    )

    backup_count: int = Field(
        default=5,
        description="Number of backup files to keep",
        ge=0,
        le=100,
    )


class Rotation(BaseModel):
    size_based: SizeBasedRotation | None = Field(
        default=None,
        description="Configuration for size-based log rotation",
    )

    time_based: TimeBasedRotation | None = Field(
        default=None,
        description="Configuration for time-based log rotation",
    )

    @model_validator(mode="after")
    def validate_rotation_config(self) -> t.Self:
        if self.size_based and self.time_based:
            raise ValueError("Only one type of rotation configuration can be provided")

        return self


class LoggingTarget(ContextMixin, BaseModel):
    logname: t.Literal["stdout", "stderr"] | os.PathLike[str] = Field(
        default="stdout",
        description="Name of the target, can be 'stdout', 'stderr', or a file path",
    )

    loglevel: t.Literal[
        "debug",
        "DEBUG",
        "info",
        "INFO",
        "warning",
        "WARNING",
        "error",
        "ERROR",
        "critical",
        "CRITICAL",
    ] = Field(
        default="info",
        description="Log level for this target",
    )

    rotation: Rotation | None = Field(
        default=None,
        description="Configuration for log rotation",
    )

    serl: bool = Field(
        default=False,
        description="Whether to serialize logs in JSON format",
    )


class LoggingConfig(BaseModel):
    targets: list[LoggingTarget] = Field(
        default_factory=lambda: [
            LoggingTarget(logname="stdout", loglevel="debug"),
            LoggingTarget(logname="stderr", loglevel="error"),
        ],
        description="List of logging targets",
    )

    def init(self) -> None:
        from loguru import logger

        if t.TYPE_CHECKING:
            from loguru import Record

        # Clear existing handlers
        logger.remove()

        def serializer(record: Record) -> str:
            rec = record.copy()
            out = {
                "message": rec["message"],
                "extra": rec["extra"],
                "time": rec["time"].isoformat(),
                "level": rec["level"].name,
            }
            return json.dumps(out, ensure_ascii=False)

        # Set up each logging target
        for target in self.targets:
            # Set up stream or file sink
            sink: t.IO[str] | os.PathLike[str]
            if target.logname == "stdout":
                sink = sys.stdout
            elif target.logname == "stderr":
                sink = sys.stderr
            else:
                sink = target.logname

            # Determine log level
            level: str = target.loglevel.upper()

            # Configure rotation if specified
            if target.rotation:
                rot = None
                if target.rotation.size_based:
                    rot = f"{target.rotation.size_based.max_size} MB"
                elif target.rotation.time_based:
                    rot = f"{target.rotation.time_based.interval} hours"
                logger.add(
                    sink,
                    retention=target.rotation.backup_count,
                    level=level,
                    rotation=rot,
                    format=serializer if target.serl else None,
                )
            else:
                logger.add(sink, level=level, serialize=target.serl)
