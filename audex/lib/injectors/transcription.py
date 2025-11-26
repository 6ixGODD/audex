from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.config import Config
    from audex.lib.transcription import Transcription


def make_transcription(config: Config) -> Transcription:
    if config.provider.transcription.provider == "dashscope":
        from audex.lib.transcription.dashscope import DashscopeParaformer

        return DashscopeParaformer(
            model=config.provider.transcription.dashscope.model,
            api_key=config.provider.transcription.dashscope.credential.api_key,
            user_agent=config.provider.transcription.dashscope.user_agent,
            workspace=config.provider.transcription.dashscope.workspace,
            max_connections=config.provider.transcription.dashscope.websocket.max_connections,
            idle_timeout=config.provider.transcription.dashscope.websocket.idle_timeout,
            drain_timeout=config.provider.transcription.dashscope.websocket.drain_timeout,
            fmt=config.provider.transcription.dashscope.session.fmt,
            sample_rate=config.core.audio.sample_rate,
            silence_duration_ms=config.provider.transcription.dashscope.session.silence_duration_ms,
            vocabulary_id=config.provider.transcription.dashscope.session.vocabulary_id,
            disfluency_removal_enabled=config.provider.transcription.dashscope.session.disfluency_removal_enabled,
            lang_hints=config.provider.transcription.dashscope.session.lang_hints,
            semantic_punctuation=config.provider.transcription.dashscope.session.semantic_punctuation,
            multi_thres_mode=config.provider.transcription.dashscope.session.multi_thres_mode,
            punctuation_pred=config.provider.transcription.dashscope.session.punctuation_pred,
            heartbeat=config.provider.transcription.dashscope.session.heartbeat,
            itn=config.provider.transcription.dashscope.session.itn,
            resources=config.provider.transcription.dashscope.session.resources,
        )

    return NotImplemented
