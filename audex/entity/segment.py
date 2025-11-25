from __future__ import annotations

import datetime

from audex import utils
from audex.entity import BaseEntity
from audex.entity import touch_after
from audex.entity.fields import DateTimeField
from audex.entity.fields import IntegerField
from audex.entity.fields import StringField


class Segment(BaseEntity):
    """Segment entity representing a continuous audio recording segment.

    Represents one continuous recording segment within a session. Since
    recording can be stopped and restarted, a session may have multiple
    segments. Each segment tracks its own timing, audio file location, and
    sequence order within the session.

    Attributes:
        id: The unique identifier of the segment. Auto-generated with "segment-"
            prefix.
        session_id: The ID of the session this segment belongs to. Foreign key
            reference to Session entity.
        sequence: The sequence number of this segment within the session.
            Starts from 1 and increments for each new segment.
        audio_key: The audio file key/path in storage. Points to the raw
            audio recording file.
        started_at: Timestamp when this segment started recording.
        ended_at: Timestamp when this segment stopped recording. None if
            still recording.
        duration_ms: Duration of the segment in milliseconds. Calculated when
            recording stops.

    Inherited Attributes:
        created_at: Timestamp when the segment was created.
        updated_at: Timestamp when the segment was last updated.

    Example:
        ```python
        # Create first segment when starting recording
        segment = Segment(
            session_id="session-xyz789",
            sequence=1,
            audio_key="audio/session-xyz789/segment-001.wav",
            started_at=utils.utcnow(),
        )

        # Stop recording and calculate duration
        segment.ended_at = utils.utcnow()
        segment.duration_ms = int(
            (segment.ended_at - segment.started_at).total_seconds()
            * 1000
        )
        segment.touch()

        # Create second segment when resuming
        segment2 = Segment(
            session_id="session-xyz789",
            sequence=2,
            audio_key="audio/session-xyz789/segment-002.wav",
            started_at=utils.utcnow(),
        )
        ```
    """

    id: str = StringField(default_factory=lambda: utils.gen_id(prefix="segment-"))
    session_id: str = StringField()
    sequence: int = IntegerField()
    audio_key: str = StringField()
    started_at: datetime.datetime = DateTimeField(default_factory=utils.utcnow)
    ended_at: datetime.datetime | None = DateTimeField(nullable=True)
    duration_ms: int | None = IntegerField(nullable=True)

    @property
    def is_recording(self) -> bool:
        """Check if this segment is currently recording.

        Returns:
            True if ended_at is None, False otherwise.
        """
        return self.ended_at is None

    @touch_after
    def incr(self) -> None:
        """Increment the sequence number of this segment by 1.

        Note:
            The updated_at timestamp is automatically updated.
        """
        self.sequence += 1

    @touch_after
    def decr(self) -> None:
        """Decrement the sequence number of this segment by 1.

        Note:
            The updated_at timestamp is automatically updated.
        """
        if self.sequence > 1:
            self.sequence -= 1
        raise ValueError("Sequence number cannot be less than 1.")

    @touch_after
    def stop(self) -> None:
        """Stop the recording of this segment by setting ended_at and
        calculating duration_ms.

        Note:
            The updated_at timestamp is automatically updated.
        """
        if self.ended_at is None:
            self.ended_at = utils.utcnow()
            self.duration_ms = int((self.ended_at - self.started_at).total_seconds() * 1000)
