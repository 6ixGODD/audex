from __future__ import annotations

import os
import pathlib
import sys
import typing as t

from pydantic import model_validator

from audex.helper.mixin import ContextMixin
from audex.helper.settings import BaseModel
from audex.helper.settings.fields import Field


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


class LoggingConfig(BaseModel):
    targets: list[LoggingTarget] = Field(
        default_factory=lambda: [
            LoggingTarget(logname="stdout", loglevel="debug"),
            LoggingTarget(logname="stderr", loglevel="error"),
            LoggingTarget(
                logname=pathlib.Path("logs/audex.jsonl"),
                loglevel="info",
                rotation=Rotation(size_based=SizeBasedRotation()),
            ),
        ],
        description="List of logging targets",
        windows_default=lambda: [
            LoggingTarget(logname="stdout", loglevel="info"),
            LoggingTarget(
                logname=pathlib.PureWindowsPath("%PROGRAMDATA%\\logs\\audex.log"),
                loglevel="info",
                rotation=Rotation(size_based=SizeBasedRotation()),
            ),
        ],
        linux_default=lambda: [
            LoggingTarget(logname="stdout", loglevel="info"),
            LoggingTarget(
                logname=pathlib.PurePosixPath("${HOME}/.local/share/audex/logs/audex.log"),
                loglevel="info",
                rotation=Rotation(size_based=SizeBasedRotation()),
            ),
        ],
    )

    def init(self) -> None:
        from loguru import logger

        if t.TYPE_CHECKING:
            pass

        # Clear existing handlers
        logger.remove()

        # Set up each logging target
        for target in self.targets:
            level = target.loglevel.upper()
            if target.logname == "stdout":
                logger.add(sys.stdout, level=level)
                continue
            if target.logname == "stderr":
                logger.add(sys.stderr, level=level)
                continue
            sink = target.logname

            # Configure rotation if specified
            if target.rotation:
                if target.rotation.size_based:
                    logger.add(
                        sink,
                        retention=target.rotation.size_based.backup_count,
                        level=level,
                        rotation=f"{target.rotation.size_based.max_size} MB",
                        serialize=True,
                    )
                elif target.rotation.time_based:
                    logger.add(
                        sink,
                        retention=target.rotation.time_based.backup_count,
                        level=level,
                        rotation=f"{target.rotation.time_based.interval} hours",
                        serialize=True,
                    )
            else:
                logger.add(sink, level=level)
