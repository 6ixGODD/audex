from __future__ import annotations

import abc
import typing as t

from audex.exceptions import AudexError
from audex.lib.transcription.types import Delta
from audex.lib.transcription.types import Done
from audex.lib.transcription.types import Start
from audex.lib.types import DuplexSession


class Transcription(abc.ABC):
    @abc.abstractmethod
    def session(
        self,
        *,
        fmt: t.Literal["pcm", "mp3"] = "pcm",
        sample_rate: t.Literal[8000, 16000, 22050, 44100, 48000] = 16000,
        silence_duration_ms: int | None = None,
        **kwargs: t.Any,
    ) -> TranscriptSession:
        pass


ReceiveType: t.TypeAlias = Start | Delta | Done


class TranscriptSession(DuplexSession[bytes, ReceiveType], abc.ABC): ...


class TranscriptionError(AudexError):
    code = 0x1001
    default_message = "Transcription service error"
