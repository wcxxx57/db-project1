"""答卷提交路由 & 公开问卷访问"""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.middlewares.auth import get_current_user, get_optional_user
from app.models.response import ResponseSubmitRequest
from app.services.response_service import (
    submit_response,
    get_response_list,
    get_response_detail,
    ResponseServiceError,
)
from app.services.survey_service import get_public_survey, SurveyServiceError
from app.utils.response import success_response, error_response


router = APIRouter()


# =========================
#  公开问卷访问（通过访问码）
# =========================
@router.get("/public/surveys/{access_code}")
def api_get_public_survey(
    access_code: str,
    current_user: Optional[dict] = Depends(get_optional_user),
):
    """通过访问码获取可填写问卷"""
    try:
        result = get_public_survey(
            access_code=access_code,
            respondent_id=current_user["user_id"] if current_user else None,
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except SurveyServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )


# =========================
#  提交答卷
# =========================
@router.post("/responses")
def api_submit_response(
    payload: ResponseSubmitRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """提交答卷（必须登录）"""
    try:
        # 获取客户端信息
        ip_address = request.client.host if request.client else None
        user_agent_header = request.headers.get("user-agent")

        result = submit_response(
            survey_id=payload.survey_id,
            access_code=payload.access_code,
            answers=[a.model_dump() for a in payload.answers],
            respondent_id=current_user["user_id"],
            is_anonymous_choice=payload.is_anonymous,
            ip_address=ip_address,
            user_agent=user_agent_header,
            completion_time=payload.completion_time,
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except ResponseServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )


# =========================
#  获取答卷列表（创建者使用）
# =========================
@router.get("/surveys/{survey_id}/responses")
def api_get_response_list(
    survey_id: str,
    current_user: dict = Depends(get_current_user),
):
    """获取某问卷的答卷列表"""
    try:
        result = get_response_list(
            survey_id=survey_id,
            creator_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except ResponseServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )


# =========================
#  获取答卷详情（创建者使用）
# =========================
@router.get("/responses/{response_id}")
def api_get_response_detail(
    response_id: str,
    current_user: dict = Depends(get_current_user),
):
    """获取答卷详情"""
    try:
        result = get_response_detail(
            response_id=response_id,
            creator_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except ResponseServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )
