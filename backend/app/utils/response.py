"""统一响应格式工具"""

from typing import Any, Optional


def success_response(data: Any = None, message: str = "success") -> dict:
    """成功响应

    返回格式：
    {
        "success": true,
        "message": "success",
        "data": { ... }
    }
    """
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(
    code: str = "UNKNOWN_ERROR",
    message: str = "未知错误",
    details: Any = None,
) -> dict:
    """错误响应

    返回格式：
    {
        "success": false,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "...",
            "details": { ... }  // 可选
        }
    }
    """
    error = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error["details"] = details
    return {
        "success": False,
        "error": error,
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
