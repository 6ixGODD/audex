from __future__ import annotations

import datetime
import typing as t

import sqlmodel as sqlm

from audex.entity.utterance import Utterance
from audex.lib.repos.tables import BaseTable
from audex.valueobj.utterance import Speaker


class UtteranceTable(BaseTable[Utterance], table=True):
    """Utterance table model for SQLite storage.

    Maps the Utterance entity to the database table with all necessary fields
    for tracking speech utterances in conversations.

    Table: utterances
    """

    __tablename__ = "utterances"

    session_id: str = sqlm.Field(
        index=True,
        max_length=50,
        description="Foreign key to session this utterance belongs to",
    )
    segment_id: str = sqlm.Field(
        index=True,
        max_length=50,
        description="Foreign key to segment containing this utterance",
    )
    sequence: int = sqlm.Field(
        nullable=False,
        description="Sequence number within session",
    )
    speaker: str = sqlm.Field(
        max_length=20,
        nullable=False,
        index=True,
        description="Speaker identification (doctor/patient)",
    )
    text: str = sqlm.Field(
        nullable=False,
        description="Transcribed text content",
    )
    confidence: float | None = sqlm.Field(
        default=None,
        nullable=True,
        description="ASR confidence score",
    )
    start_time_ms: int = sqlm.Field(
        nullable=False,
        description="Start time in segment (milliseconds)",
    )
    end_time_ms: int = sqlm.Field(
        nullable=False,
        description="End time in segment (milliseconds)",
    )
    timestamp: datetime.datetime = sqlm.Field(
        nullable=False,
        description="Absolute timestamp of utterance",
    )

    @classmethod
    def from_entity(cls, entity: Utterance) -> t.Self:
        """Convert Utterance entity to table model.

        Args:
            entity: The Utterance entity to convert.

        Returns:
            UtteranceTable instance.
        """
        return cls(
            id=entity.id,
            session_id=entity.session_id,
            segment_id=entity.segment_id,
            sequence=entity.sequence,
            speaker=entity.speaker.value,
            text=entity.text,
            confidence=entity.confidence,
            start_time_ms=entity.start_time_ms,
            end_time_ms=entity.end_time_ms,
            timestamp=entity.timestamp,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def to_entity(self) -> Utterance:
        """Convert table model to Utterance entity.

        Returns:
            Utterance entity instance.
        """
        return Utterance(
            id=self.id,
            session_id=self.session_id,
            segment_id=self.segment_id,
            sequence=self.sequence,
            speaker=Speaker.parse(self.speaker),
            text=self.text,
            confidence=self.confidence,
            start_time_ms=self.start_time_ms,
            end_time_ms=self.end_time_ms,
            timestamp=self.timestamp,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def update(self, entity: Utterance) -> None:
        """Update table model fields from Utterance entity.

        Args:
            entity: The Utterance entity with updated data.
        """
        self.session_id = entity.session_id
        self.segment_id = entity.segment_id
        self.sequence = entity.sequence
        self.speaker = entity.speaker.value
        self.text = entity.text
        self.confidence = entity.confidence
        self.start_time_ms = entity.start_time_ms
        self.end_time_ms = entity.end_time_ms
        self.timestamp = entity.timestamp
        self.updated_at = entity.updated_at


TABLES: set[type[sqlm.SQLModel]] = {UtteranceTable}
"""Set of all table models for the repository."""
