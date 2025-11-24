from __future__ import annotations

import datetime
import typing as t

import sqlmodel as sqlm

from audex.entity.segment import Segment
from audex.lib.repos.tables import BaseTable


class SegmentTable(BaseTable[Segment], table=True):
    """Segment table model for SQLite storage.

    Maps the Segment entity to the database table with all necessary fields
    for tracking audio recording segments within sessions.

    Table: segments
    """

    __tablename__ = "segments"

    session_id: str = sqlm.Field(
        foreign_key="sessions.id",
        index=True,
        max_length=50,
        description="Foreign key to session this segment belongs to",
    )
    sequence: int = sqlm.Field(
        nullable=False,
        description="Sequence number within session",
    )
    audio_key: str = sqlm.Field(
        max_length=500,
        nullable=False,
        description="Audio file key/path in storage",
    )
    started_at: datetime.datetime = sqlm.Field(
        nullable=False,
        description="Timestamp when segment started recording",
    )
    ended_at: datetime.datetime | None = sqlm.Field(
        default=None,
        nullable=True,
        description="Timestamp when segment stopped recording",
    )
    duration_ms: int | None = sqlm.Field(
        default=None,
        nullable=True,
        description="Duration of segment in milliseconds",
    )

    @classmethod
    def from_entity(cls, entity: Segment) -> t.Self:
        """Convert Segment entity to table model.

        Args:
            entity: The Segment entity to convert.

        Returns:
            SegmentTable instance.
        """
        return cls(
            id=entity.id,
            session_id=entity.session_id,
            sequence=entity.sequence,
            audio_key=entity.audio_key,
            started_at=entity.started_at,
            ended_at=entity.ended_at,
            duration_ms=entity.duration_ms,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> Segment:
        """Convert table model to Segment entity.

        Returns:
            Segment entity instance.
        """
        return Segment(
            id=self.id,
            session_id=self.session_id,
            sequence=self.sequence,
            audio_key=self.audio_key,
            started_at=self.started_at,
            ended_at=self.ended_at,
            duration_ms=self.duration_ms,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


TABLES: set[type[sqlm.SQLModel]] = {SegmentTable}
"""Set of all table models for the repository."""
