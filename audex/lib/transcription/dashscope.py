from __future__ import annotations

import asyncio
import contextlib
import typing as t

from pydantic import BaseModel
from pydantic import TypeAdapter

from audex import utils
from audex.helper.mixin import LoggingMixin
from audex.helper.stream import AsyncStream
from audex.lib.transcription import Delta
from audex.lib.transcription import Done
from audex.lib.transcription import ReceiveType
from audex.lib.transcription import Start
from audex.lib.transcription import Transcription
from audex.lib.transcription import TranscriptionError
from audex.lib.transcription import TranscriptSession
from audex.lib.websocket.connection import WebsocketConnection
from audex.lib.websocket.pool import WebsocketConnectionPool


class InvalidParamError(TranscriptionError):
    default_message = "Invalid transcription parameters"

    def __init__(
        self,
        message: str | None = None,
        params: dict[str, t.Any] | None = None,
    ):
        super().__init__(message or self.default_message)
        self.params = params or {}


class RunTaskPayloadParams(BaseModel):
    format: t.Literal["pcm", "wav", "mp3", "opus", "speex", "aac", "amr"] = "pcm"
    sample_rate: int = 16000
    vocabulary_id: str | None = None
    disfluency_removal_enabled: bool | None = None
    language_hints: list[t.Literal["zh", "en", "ja", "yue", "ko", "de", "fr", "ru"]] | None = None
    semantic_punctuation_enabled: bool | None = None
    max_sentence_silence: int | None = None
    multi_threshold_mode_enabled: bool | None = None
    punctuation_prediction_enabled: bool | None = None
    heartbeat: bool | None = None
    inverse_text_normalization_enabled: bool | None = None


class RunTaskPayloadResource(BaseModel):
    resource_id: str
    resource_type: t.Literal["asr_phrase"] = "asr_phrase"


class RunTaskPayload(BaseModel):
    task_group: t.Literal["audio"] = "audio"
    task: t.Literal["asr"] = "asr"
    function: t.Literal["recognition"] = "recognition"
    model: str = "paraformer-realtime-v2"
    parameters: RunTaskPayloadParams = RunTaskPayloadParams()
    resources: list[RunTaskPayloadResource] = []
    input: dict[str, object] = {}


class RunTaskHeader(BaseModel):
    task_id: str
    action: t.Literal["run-task"] = "run-task"
    streaming: t.Literal["duplex"] = "duplex"


class RunTask(BaseModel):
    header: RunTaskHeader
    payload: RunTaskPayload


class FinishTaskHeader(BaseModel):
    task_id: str
    action: t.Literal["finish-task"] = "finish-task"
    streaming: t.Literal["duplex"] = "duplex"


class FinishTaskPayload(BaseModel):
    input: dict[str, object] = {}


class FinishTask(BaseModel):
    header: FinishTaskHeader
    payload: FinishTaskPayload = FinishTaskPayload()


class BaseServerHeader(BaseModel):
    task_id: str | None = None
    event: t.Literal["task-started", "result-generated", "task-finished", "task-failed"]
    attributes: dict[str, t.Any]


class BaseServerMessage(BaseModel):
    header: BaseServerHeader


class TaskStartedHeader(BaseServerHeader):
    event: t.Literal["task-started"]


class TaskStarted(BaseServerMessage):
    header: TaskStartedHeader


class ResultGeneratedHeader(BaseServerHeader):
    event: t.Literal["result-generated"]


class ResultGeneratedPayloadOutputSentence(BaseModel):
    begin_time: int  # in milliseconds
    end_time: int | None
    text: str
    words: list[dict[str, object]] | None


class ResultGeneratedPayloadOutput(BaseModel):
    sentence: ResultGeneratedPayloadOutputSentence


class ResultGeneratedPayload(BaseModel):
    output: ResultGeneratedPayloadOutput
    usage: t.Any = None


class ResultGenerated(BaseServerMessage):
    header: ResultGeneratedHeader
    payload: ResultGeneratedPayload


class TaskFinishedHeader(BaseServerHeader):
    event: t.Literal["task-finished"]


class TaskFinished(BaseServerMessage):
    header: TaskFinishedHeader


class TaskFailedHeader(BaseServerHeader):
    event: t.Literal["task-failed"]
    error_code: str
    error_message: str


class TaskFailed(BaseServerMessage):
    header: TaskFailedHeader


ServerMessage = TaskStarted | ResultGenerated | TaskFinished | TaskFailed
adapter: TypeAdapter[ServerMessage] = TypeAdapter(ServerMessage)


def parse_server_message(
    data: t.AnyStr,
) -> TaskStarted | ResultGenerated | TaskFinished | TaskFailed:
    try:
        return adapter.validate_json(data)
    except Exception as e:
        print("=" * 20)
        print(str(e))
        print(data)
        print("=" * 20)

        raise


class DashscopeParaformer(LoggingMixin, Transcription):
    __logtag__ = "audex.lib.transcript.dashscope"

    def __init__(
        self,
        *,
        model: str = "paraformer-realtime-v2",
        url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
        api_key: str,
        user_agent: str | None = None,
        workspace: str | None = None,
        max_connections: int = 1000,
        idle_timeout: int = 60,
        drain_timeout: float = 5.0,
        # Runtime parameters
        fmt: t.Literal["pcm", "wav", "mp3", "opus", "speex", "aac", "amr"] = "pcm",
        sample_rate: int = 8000,
        silence_duration_ms: int | None = None,
        vocabulary_id: str | None = None,
        disfluency_removal_enabled: bool | None = None,
        lang_hints: list[t.Literal["zh", "en", "ja", "yue", "ko", "de", "fr", "ru"]] | None = None,
        semantic_punctuation: bool | None = None,
        multi_thres_mode: bool | None = None,
        punctuation_pred: bool | None = None,
        heartbeat: bool | None = None,
        itn: bool | None = None,
        resources: list[str] | None = None,
        **kwargs: t.Any,
    ):
        super().__init__()
        self.model = model
        self.api_key = api_key
        self.user_agent = user_agent

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-DashScope-DataInspection": "enable",
        }
        if self.user_agent:
            self.headers["User-Agent"] = self.user_agent
        if workspace:
            self.headers["X-DashScope-Workspace"] = workspace

        self.pool = WebsocketConnectionPool(
            uri=url,
            headers=self.headers,
            idle_timeout=idle_timeout,
            max_connections=max_connections,
            check_server_data_on_release=True,
            drain_timeout=drain_timeout,
            **kwargs,
        )

        self.fmt = fmt
        self.sample_rate = sample_rate
        self.silence_duration_ms = silence_duration_ms
        self.vocabulary_id = vocabulary_id
        self.disfluency_removal_enabled = disfluency_removal_enabled
        self.lang_hints = lang_hints
        self.semantic_punctuation = semantic_punctuation
        self.multi_thres_mode = multi_thres_mode
        self.punctuation_pred = punctuation_pred
        self.heartbeat = heartbeat
        self.itn = itn
        self.resources = resources

    def verify(
        self,
        model: str,
        sr: int,
        has_lang_hints: bool,
        semantic_punctuation: bool | None = None,
        multi_thres_mode: bool | None = None,
        punctuation_pred: bool | None = None,
        heartbeat: bool | None = None,
        itn: bool | None = None,
    ) -> None:
        v2_params = [semantic_punctuation, multi_thres_mode, punctuation_pred, heartbeat, itn]
        if model not in {"paraformer-realtime-v2", "paraformer-realtime-8k-v2"} and any(
            p is not None for p in v2_params
        ):
            error_msg = (
                'Only "paraformer-realtime-v2" and "paraformer-realtime-8k-v2" support v2 parameters ('
                "`semantic_punctuation`, `multi_thres_mode`, `punctuation_pred`, `heartbeat`, `itn`)."
            )
            self.logger.error(f"Invalid parameter combination: {error_msg}")
            raise InvalidParamError(message=error_msg, params={"model": model})

        if model in {"paraformer-realtime-8k-v1", "paraformer-realtime-8k-v2"} and sr != 8000:
            error_msg = "The sample rate for 8k models must be 8000 Hz."
            self.logger.error(f"Invalid sample rate: {error_msg}")
            raise InvalidParamError(message=error_msg, params={"sample_rate": sr})

        if model == "paraformer-realtime-v1" and sr != 16000:
            error_msg = 'The sample rate for "paraformer-realtime-v1" must be 16000 Hz.'
            self.logger.error(f"Invalid sample rate: {error_msg}")
            raise InvalidParamError(message=error_msg, params={"sample_rate": sr})

        if model != "paraformer-realtime-v2" and has_lang_hints:
            error_msg = 'Only "paraformer-realtime-v2" supports `lang_hints` parameter.'
            self.logger.error(f"Invalid parameter combination: {error_msg}")
            raise InvalidParamError(message=error_msg, params={"lang_hints": ""})

    def session(
        self,
        *,
        fmt: t.Literal["pcm", "mp3"] = "pcm",
        sample_rate: int = 16000,
        silence_duration_ms: int | None = None,
        vocabulary_id: str | None = None,
    ) -> TranscriptSession:
        self.verify(
            model=self.model,
            sr=self.sample_rate or sample_rate,
            has_lang_hints=self.lang_hints is not None,
            semantic_punctuation=self.semantic_punctuation,
            multi_thres_mode=self.multi_thres_mode,
            punctuation_pred=self.punctuation_pred,
            heartbeat=self.heartbeat,
            itn=self.itn,
        )

        return DashscopeParaformerSession(
            pool=self.pool,
            model=self.model,
            fmt=self.fmt or fmt,
            sample_rate=self.sample_rate or sample_rate,
            vocabulary_id=self.vocabulary_id or vocabulary_id,
            disfluency_removal_enabled=self.disfluency_removal_enabled,
            lang_hints=self.lang_hints,
            semantic_punctuation=self.semantic_punctuation,
            max_sentence_silence=self.silence_duration_ms or silence_duration_ms,
            multi_thres_mode=self.multi_thres_mode,
            punctuation_pred=self.punctuation_pred,
            heartbeat=self.heartbeat,
            itn=self.itn,
            resources=self.resources,
        )


class DashscopeParaformerSession(LoggingMixin, TranscriptSession):
    __logtag__ = "audex.lib.transcript.dashscope.session"

    def __init__(
        self,
        *,
        pool: WebsocketConnectionPool,
        model: str,
        fmt: t.Literal["pcm", "wav", "mp3", "opus", "speex", "aac", "amr"],
        sample_rate: int,
        vocabulary_id: str | None = None,
        disfluency_removal_enabled: bool | None = None,
        lang_hints: list[t.Literal["zh", "en", "ja", "yue", "ko", "de", "fr", "ru"]] | None = None,
        semantic_punctuation: bool | None = None,
        max_sentence_silence: int | None = None,
        multi_thres_mode: bool | None = None,
        punctuation_pred: bool | None = None,
        heartbeat: bool | None = None,
        itn: bool | None = None,
        resources: list[str] | None = None,
    ):
        super().__init__()
        self.pool = pool
        self.model = model
        self.format = fmt
        self.sample_rate = sample_rate
        self.vocabulary_id = vocabulary_id
        self.disfluency_removal_enabled = disfluency_removal_enabled
        self.lang_hints = lang_hints
        self.semantic_punctuation = semantic_punctuation
        self.max_sentence_silence = max_sentence_silence
        self.multi_thres_mode = multi_thres_mode
        self.punctuation_pred = punctuation_pred
        self.heartbeat = heartbeat
        self.itn = itn
        self.resources = resources

        self.task_id: str | None = None
        self.connection: WebsocketConnection | None = None
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        async with self.lock:
            self.logger.debug("Starting DashscopeParaformerSession")
            self.connection = await self.pool.acquire()
            self.task_id = utils.gen_id()

            resource_objs = []  # type: list[RunTaskPayloadResource]
            if self.resources:
                for res_id in self.resources:
                    resource_objs.append(RunTaskPayloadResource(resource_id=res_id))

            payload_params = RunTaskPayloadParams(
                format=self.format,
                sample_rate=self.sample_rate,
                vocabulary_id=self.vocabulary_id,
                disfluency_removal_enabled=self.disfluency_removal_enabled,
                language_hints=self.lang_hints,
                semantic_punctuation_enabled=self.semantic_punctuation,
                max_sentence_silence=self.max_sentence_silence,
                multi_threshold_mode_enabled=self.multi_thres_mode,
                punctuation_prediction_enabled=self.punctuation_pred,
                heartbeat=self.heartbeat,
                inverse_text_normalization_enabled=self.itn,
            )
            payload = RunTaskPayload(
                model=self.model,
                parameters=payload_params,
                resources=resource_objs,
            )
            header = RunTaskHeader(task_id=self.task_id)
            run_task = RunTask(header=header, payload=payload)
            with self.logger.catch(reraise=True, level="ERROR", message="Failed to start session"):
                _, server_msg = await asyncio.gather(
                    self.connection.send(run_task.model_dump_json(exclude_none=True)),
                    self.connection.recv(),
                )

            msg = parse_server_message(server_msg)

            if not isinstance(msg, TaskStarted):
                raise TranscriptionError(f"Unexpected server message: {server_msg}")

            if not msg.header.task_id == self.task_id:
                raise TranscriptionError(
                    f"Task ID mismatch: expected {self.task_id}, got {msg.header.task_id}"
                )

    async def finish(self) -> None:
        if not self.connection or not self.task_id:
            return

        async with self.lock:
            self.logger.debug("Finishing DashscopeParaformerSession")
            header = FinishTaskHeader(task_id=self.task_id)
            finish_task = FinishTask(header=header)

            with self.logger.catch(reraise=True, level="ERROR", message="Failed to finish session"):
                await self.connection.send(finish_task.model_dump_json(exclude_none=True))

    async def close(self) -> None:
        async with self.lock:
            self.logger.debug("Closing DashscopeParaformerSession")
            if self.connection:
                await self.pool.release(self.connection)
                self.connection = None
            self.task_id = None

    async def send(self, message: bytes) -> None:
        if not self.connection or not self.task_id:
            raise TranscriptionError("Session not started")

        with self.logger.catch(reraise=True, level="ERROR", message="Failed to send audio data"):
            await self.connection.send(message)

    def receive(self) -> AsyncStream[ReceiveType]:
        return AsyncStream(self._receive_iter())

    async def _receive_iter(self) -> t.AsyncGenerator[ReceiveType, None]:
        await asyncio.sleep(0.0)

        if not self.connection or not self.task_id:
            raise TranscriptionError("Session not started")

        started = False
        total_duration = 0.0

        while True:
            self.logger.debug("Waiting for server message")
            with contextlib.suppress(asyncio.TimeoutError):
                server_msg = await asyncio.wait_for(self.connection.recv(), timeout=30.0)

            msg = parse_server_message(server_msg)
            if not msg.header.task_id == self.task_id:
                raise TranscriptionError(
                    f"Task ID mismatch: expected {self.task_id}, got {msg.header.task_id}"
                )

            if isinstance(msg, ResultGenerated):
                if not started:
                    self.logger.debug("Transcription started")
                    started = True
                    yield Start(at=utils.utcnow().timestamp())

                sentence = msg.payload.output.sentence
                interim = sentence.end_time is None

                self.logger.debug(
                    f"Transcription result received: "
                    f"text='{sentence.text}', "
                    f"begin_time={sentence.begin_time}, "
                    f"end_time={sentence.end_time}, "
                    f"interim={interim}",
                )
                yield Delta(
                    from_at=sentence.begin_time / 1000.0,
                    to_at=(sentence.end_time / 1000.0) if sentence.end_time else None,
                    text=sentence.text,
                    interim=interim,
                )

                if not interim:
                    self.logger.debug("Final transcription received, continuing to listen")
                    total_duration += (sentence.end_time - sentence.begin_time) / 1000.0
                    yield Done()

            elif isinstance(msg, TaskFinished):
                if msg.header.task_id != self.task_id:
                    raise TranscriptionError(
                        f"Task ID mismatch: expected {self.task_id}, got {msg.header.task_id}"
                    )

                self.logger.debug("Transcription task finished by server")
                break

            elif isinstance(msg, TaskFailed):
                self.logger.error(
                    f"Transcription task failed: "
                    f"error_code={msg.header.error_code}, "
                    f"error_message={msg.header.error_message}"
                )
                raise TranscriptionError(
                    f"Transcription task failed: {msg.header.error_message} "
                    f"(code: {msg.header.error_code})"
                )

            else:
                self.logger.error(f"Unexpected server message: {server_msg}")
                raise TranscriptionError(f"Unexpected server message: {server_msg}")
