from __future__ import annotations

import abc
import typing as t

from audex.exceptions import AudexError
from audex.lib.transcription.events import Delta
from audex.lib.transcription.events import Done
from audex.lib.transcription.events import Start
from audex.types import DuplexAbstractSession


class Transcription(abc.ABC):
    @abc.abstractmethod
    def session(
        self,
        *,
        fmt: t.Literal["pcm", "mp3"] = "pcm",
        sample_rate: int = 16000,
        silence_duration_ms: int | None = None,
        vocabulary_id: str | None = None,
    ) -> TranscriptSession:
        pass


ReceiveType: t.TypeAlias = Start | Delta | Done


class TranscriptSession(DuplexAbstractSession[bytes, ReceiveType], abc.ABC): ...


class TranscriptionError(AudexError):
    default_message = "Transcription service error"
