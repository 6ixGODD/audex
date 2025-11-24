from __future__ import annotations


class Start:
    """Indicates the start of the transcription process.

    Attributes:
        at (float): The timestamp when the transcription started (in seconds).
    """

    __slots__ = ("at",)

    def __init__(self, *, at: float) -> None:
        self.at = at


class Delta:
    """Delta event representing a partial transcription update.

    Attributes:
        from_at (float): The starting timestamp of the transcription segment
            (in seconds).
        to_at (float): The ending timestamp of the transcription segment (in
            seconds).
        text (str): The transcribed text for the segment.
        interim (bool): Indicates if the transcription is interim (True) or
            final (False).
    """

    __slots__ = (
        "from_at",
        "interim",
        "text",
        "to_at",
    )

    def __init__(self, *, from_at: float, to_at: float, text: str, interim: bool) -> None:
        self.from_at = from_at
        self.to_at = to_at
        self.text = text
        self.interim = interim


class Done:
    """Indicates the completion of the transcription process."""

    __slots__ = ()
