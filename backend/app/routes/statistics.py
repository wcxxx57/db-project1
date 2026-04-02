"""统计分析路由"""

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.middlewares.auth import get_current_user
from app.services.statistics_service import (
    get_survey_statistics,
    get_question_statistics,
    StatisticsServiceError,
)
from app.utils.response import success_response, error_response


router = APIRouter()


@router.get("/surveys/{survey_id}/statistics")
def api_get_survey_statistics(
    survey_id: str,
    current_user: dict = Depends(get_current_user),
):
    """获取问卷整体统计"""
    try:
        result = get_survey_statistics(
            survey_id=survey_id,
            creator_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except StatisticsServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )


@router.get("/surveys/{survey_id}/questions/{question_id}/statistics")
def api_get_question_statistics(
    survey_id: str,
    question_id: str,
    current_user: dict = Depends(get_current_user),
):
    """获取单个题目的统计"""
    try:
        result = get_question_statistics(
            survey_id=survey_id,
            question_id=question_id,
            creator_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except StatisticsServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )
