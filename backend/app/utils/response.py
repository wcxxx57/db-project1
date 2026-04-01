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
        "code": 200,
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


# 常用错误码
class ErrorCodes:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    DUPLICATE = "DUPLICATE"
    SURVEY_CLOSED = "SURVEY_CLOSED"
    SURVEY_EXPIRED = "SURVEY_EXPIRED"
    SURVEY_NOT_PUBLISHED = "SURVEY_NOT_PUBLISHED"
    ALREADY_SUBMITTED = "ALREADY_SUBMITTED"
