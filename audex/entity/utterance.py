from __future__ import annotations

import datetime

from audex import utils
from audex.entity import BaseEntity
from audex.entity.fields import DateTimeField
from audex.entity.fields import FloatField
from audex.entity.fields import IntegerField
from audex.entity.fields import StringBackedField
from audex.entity.fields import StringField
from audex.valueobj.utterance import Speaker


class Utterance(BaseEntity):
    """Utterance entity representing a single speech utterance in
    conversation.

    Represents one continuous speech segment from either the doctor or patient,
    as recognized by ASR (Automatic Speech Recognition) and speaker verification.
    Each utterance contains the transcribed text, speaker identification,
    timing information, and confidence scores.

    Attributes:
        id: The unique identifier of the utterance. Auto-generated with
            "utterance-" prefix.
        session_id: The ID of the session this utterance belongs to. Foreign
            key reference to Session entity.
        segment_id: The ID of the audio segment containing this utterance.
            Foreign key reference to Segment entity.
        sequence: The sequence number of this utterance within the session.
            Starts from 1 and increments for each new utterance.
        speaker: The identified speaker (DOCTOR or PATIENT). Determined by
            voiceprint verification against doctor's registered voiceprint.
        text: The transcribed text content from ASR.
        confidence: ASR confidence score, typically between 0.0 and 1.0.
            Higher values indicate more confident transcription.
        start_time_ms: Start time of the utterance within the audio segment,
            in milliseconds from segment start.
        end_time_ms: End time of the utterance within the audio segment,
            in milliseconds from segment start.
        timestamp: Absolute timestamp when the utterance occurred in the
            session timeline.

    Inherited Attributes:
        created_at: Timestamp when the utterance was created.
        updated_at: Timestamp when the utterance was last updated.

    Example:
        ```python
        # Create doctor utterance
        utterance = Utterance(
            session_id="session-xyz789",
            segment_id="segment-abc123",
            sequence=1,
            speaker=Speaker.DOCTOR,
            text="您好，今天哪里不舒服？",
            confidence=0.95,
            start_time_ms=1000,
            end_time_ms=3500,
            timestamp=utils.utcnow(),
        )

        # Create patient utterance
        utterance2 = Utterance(
            session_id="session-xyz789",
            segment_id="segment-abc123",
            sequence=2,
            speaker=Speaker.PATIENT,
            text="医生，我最近总是头疼。",
            confidence=0.88,
            start_time_ms=4000,
            end_time_ms=6800,
            timestamp=utils.utcnow(),
        )

        # Check speaker
        if utterance.is_doctor:
            print("This is doctor speaking")
        if utterance2.is_patient:
            print("This is patient speaking")
        ```
    """

    id: str = StringField(immutable=True, default_factory=lambda: utils.gen_id(prefix="utterance-"))
    session_id: str = StringField()
    segment_id: str = StringField()
    sequence: int = IntegerField()
    speaker: Speaker = StringBackedField(Speaker)
    text: str = StringField()
    confidence: float | None = FloatField(nullable=True)
    start_time_ms: int = IntegerField()
    end_time_ms: int = IntegerField()
    timestamp: datetime.datetime = DateTimeField(default_factory=utils.utcnow)

    @property
    def duration_ms(self) -> int:
        """Calculate the duration of this utterance in milliseconds.

        Returns:
            Duration in milliseconds.
        """
        return self.end_time_ms - self.start_time_ms

    @property
    def is_doctor(self) -> bool:
        """Check if the speaker is the doctor.

        Returns:
            True if speaker is DOCTOR, False otherwise.
        """
        return self.speaker == Speaker.DOCTOR

    @property
    def is_patient(self) -> bool:
        """Check if the speaker is the patient.

        Returns:
            True if speaker is PATIENT, False otherwise.
        """
        return self.speaker == Speaker.PATIENT
