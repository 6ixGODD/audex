from __future__ import annotations


class ErrorMessages:
    """Error messages in Chinese for session service."""

    # Session errors
    SESSION_NOT_FOUND = "未找到指定的会话"
    SESSION_CREATE_FAILED = "创建会话失败，请稍后重试"
    SESSION_UPDATE_FAILED = "更新会话失败，请稍后重试"
    SESSION_DELETE_FAILED = "删除会话失败，请稍后重试"

    # Recording errors
    RECORDING_START_FAILED = "启动录音失败"
    RECORDING_STOP_FAILED = "停止录音失败"
    RECORDING_IN_PROGRESS = "录音正在进行中，请先停止当前录音"

    # Segment errors
    SEGMENT_NOT_FOUND = "未找到音频片段"
    SEGMENT_CREATE_FAILED = "保存音频片段失败"

    # Utterance errors
    UTTERANCE_STORE_FAILED = "保存对话记录失败"

    # Transcription errors
    TRANSCRIPTION_START_FAILED = "启动语音识别失败"
    TRANSCRIPTION_FAILED = "语音识别失败"

    # VPR errors
    SPEAKER_VERIFICATION_FAILED = "说话人识别失败"
    NO_VOICEPRINT_FOUND = "未找到声纹注册，请先注册声纹"

    # Session errors
    NO_ACTIVE_SESSION = "登录状态已过期，请重新登录"
