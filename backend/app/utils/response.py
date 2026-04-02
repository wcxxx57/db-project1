"""统一响应格式工具"""

from typing import Any, Optional


def success_response(data: Any = None, message: str = "success") -> dict:
    """成功响应

    返回格式：
    {
        "code": 200,
        "message": "success",
        "data": { ... }
    }
    """
    return {
        "code": 0,
        "message": message,
        "data": data,
    }


def error_response(
    code: int = 400,
    message: str = "未知错误",
    data: Any = None,
) -> dict:
    """错误响应

    返回格式：
    {
        "code": 400,
        "message": "错误信息",
        "data": null
    }
    """
    return {
        "code": code,
        "message": message,
        "data": data,
    }


class ErrorCodes:
    """业务错误码（与 API 文档保持一致）"""

    USERNAME_EXISTS = 1001
    INVALID_CREDENTIALS = 1002
    INVALID_TOKEN = 1003

    SURVEY_NOT_FOUND = 2001
    NO_PERMISSION = 2002
    SURVEY_CLOSED = 2003
    SURVEY_EXPIRED = 2004
    INVALID_ACCESS_CODE = 2005

    ANSWER_VALIDATION_FAILED = 3001
    DUPLICATE_SUBMISSION = 3002
    REQUIRED_QUESTION_MISSING = 3003
    LOGIN_REQUIRED = 3004
