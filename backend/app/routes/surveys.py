"""问卷管理路由"""

from fastapi import APIRouter, Depends, Query, Path
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from typing import Optional

from app.middlewares.auth import get_current_user
from app.models.survey import SurveyCreateRequest, SurveyResponse, SurveyListItem
from app.services.survey_service import (
    create_survey,
    get_user_surveys,
    get_survey,
    publish_survey,
    close_survey,
    delete_survey,
    SurveyServiceError
)
from app.utils.response import success_response, error_response


router = APIRouter()


@router.post("")
def api_create_survey(
    payload: SurveyCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["user_id"]
        survey_data = create_survey(user_id=user_id, request=payload)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=survey_data)),
        )
    except SurveyServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )


@router.get("/my")
def api_get_my_surveys(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["user_id"]
        surveys_data = get_user_surveys(user_id=user_id, page=page, page_size=page_size)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=surveys_data)),
        )
    except SurveyServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )


@router.get("/{survey_id}")
def api_get_survey(
    survey_id: str = Path(..., description="问卷ID"),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["user_id"]
        survey_data = get_survey(survey_id=survey_id, user_id=user_id)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=survey_data)),
        )
    except SurveyServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )


@router.post("/{survey_id}/publish")
def api_publish_survey(
    survey_id: str = Path(..., description="问卷ID"),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["user_id"]
        survey_data = publish_survey(survey_id=survey_id, user_id=user_id)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=survey_data)),
        )
    except SurveyServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )


@router.post("/{survey_id}/close")
def api_close_survey(
    survey_id: str = Path(..., description="问卷ID"),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["user_id"]
        survey_data = close_survey(survey_id=survey_id, user_id=user_id)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=survey_data)),
        )
    except SurveyServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )


@router.delete("/{survey_id}")
def api_delete_survey(
    survey_id: str = Path(..., description="问卷ID"),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["user_id"]
        delete_survey(survey_id=survey_id, user_id=user_id)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=None)),
        )
    except SurveyServiceError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(code=exc.business_code, message=exc.message),
        )
