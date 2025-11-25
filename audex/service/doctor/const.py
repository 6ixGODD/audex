from __future__ import annotations


class InvalidCredentialReasons:
    """Constants for invalid credential reasons."""

    DEFAULT = "default"
    DOCTOR_NOT_FOUND = "doctor_not_found"
    INVALID_PASSWORD = "invalid_password"
    ACCOUNT_INACTIVE = "account_inactive"


class ErrorMessages:
    """Error messages in Chinese for doctor service."""

    # Authentication errors
    ACCOUNT_NOT_FOUND = "账号不存在，请检查工号后重试"
    INVALID_PASSWORD = "密码错误，请重新输入"
    ACCOUNT_INACTIVE = "账号已被停用，请联系管理员"
    OLD_PASSWORD_INCORRECT = "原密码错误"

    # Session errors
    NO_ACTIVE_SESSION = "登录状态已过期，请重新登录"

    # Doctor errors
    DOCTOR_NOT_FOUND = "未找到医生账号"
    DOCTOR_DELETE_FAILED = "删除医生账号失败，请稍后重试"

    # Voiceprint errors
    VOICEPRINT_NOT_FOUND = "未找到有效的声纹注册"
    VOICEPRINT_ENROLL_FAILED = "声纹注册失败"
    VOICEPRINT_UPDATE_FAILED = "声纹更新失败"

    # Registration errors
    DUPLICATE_EID = "该工号已被注册"
    REGISTRATION_FAILED = "注册失败，请稍后重试"
