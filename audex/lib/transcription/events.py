from __future__ import annotations


class Start:
    """Indicates the start of a transcription utterance.

    Attributes:
        utterance_id: Unique ID for this utterance.
        started_at: Absolute timestamp when transcription started (UNIX
            timestamp).
    """

    __slots__ = ("started_at", "utterance_id")

    def __init__(self, *, utterance_id: str, started_at: float) -> None:
        self.utterance_id = utterance_id
        self.started_at = started_at


class Delta:
    """Delta event representing a partial transcription update.

    Attributes:
        utterance_id: ID of the utterance this delta belongs to.
        offset_begin: Start offset from utterance start (in seconds).
        offset_end: End offset from utterance start (in seconds, None for
            interim).
        text: The transcribed text for the segment.
        interim: Whether this is interim (True) or final (False).
    """

    __slots__ = ("interim", "offset_begin", "offset_end", "text", "utterance_id")

    def __init__(
        self,
        *,
        utterance_id: str,
        offset_begin: float,
        offset_end: float | None,
        text: str,
        interim: bool,
    ) -> None:
        self.utterance_id = utterance_id
        self.offset_begin = offset_begin
        self.offset_end = offset_end
        self.text = text
        self.interim = interim


class Done:
    """Indicates the completion of a transcription utterance.

    Attributes:
        utterance_id: ID of the completed utterance.
        ended_at: Absolute timestamp when transcription ended (UNIX timestamp).
    """

    __slots__ = ("ended_at", "utterance_id")

    def __init__(self, *, utterance_id: str, ended_at: float) -> None:
        self.utterance_id = utterance_id
        self.ended_at = ended_at
