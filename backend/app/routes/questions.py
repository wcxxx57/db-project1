"""题目管理路由（第二阶段新增）"""

from fastapi import APIRouter, Depends, Path, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.middlewares.auth import get_current_user
from app.models.question import (
    QuestionCreateRequest,
    QuestionNewVersionRequest,
    QuestionShareRequest,
    QuestionUnshareRequest,
)
from app.services.question_service import (
    create_question,
    get_my_questions,
    get_shared_questions,
    get_banked_questions,
    get_question_detail,
    create_new_version,
    get_version_history,
    restore_version,
    share_question,
    unshare_question,
    add_to_bank,
    remove_from_bank,
    get_question_usage,
    delete_question,
    QuestionServiceError,
)
from app.utils.response import success_response, error_response


router = APIRouter()


def _handle_error(exc: QuestionServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=error_response(code=exc.business_code, message=exc.message),
    )


@router.post("")
def api_create_question(
    payload: QuestionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """创建题目"""
    try:
        result = create_question(
            user_id=current_user["user_id"],
            data=payload.model_dump(),
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.get("/my")
def api_get_my_questions(
    current_user: dict = Depends(get_current_user),
):
    """查询我创建的题目"""
    try:
        result = get_my_questions(user_id=current_user["user_id"])
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.get("/shared")
def api_get_shared_questions(
    current_user: dict = Depends(get_current_user),
):
    """查询共享给我的题目"""
    try:
        result = get_shared_questions(user_id=current_user["user_id"])
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.get("/bank")
def api_get_banked_questions(
    current_user: dict = Depends(get_current_user),
):
    """查询我的题库"""
    try:
        result = get_banked_questions(user_id=current_user["user_id"])
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.get("/{question_id}")
def api_get_question_detail(
    question_id: str = Path(..., description="题目谱系ID"),
    current_user: dict = Depends(get_current_user),
):
    """查询题目详情"""
    try:
        result = get_question_detail(
            question_id=question_id,
            user_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.post("/{question_id}/versions")
def api_create_new_version(
    payload: QuestionNewVersionRequest,
    question_id: str = Path(..., description="题目谱系ID"),
    current_user: dict = Depends(get_current_user),
):
    """创建题目新版本"""
    try:
        result = create_new_version(
            question_id=question_id,
            user_id=current_user["user_id"],
            data=payload.model_dump(),
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.get("/{question_id}/versions")
def api_get_version_history(
    question_id: str = Path(..., description="题目谱系ID"),
    current_user: dict = Depends(get_current_user),
):
    """查询版本历史"""
    try:
        result = get_version_history(
            question_id=question_id,
            user_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.post("/{question_id}/versions/{version_number}/restore")
def api_restore_version(
    question_id: str = Path(..., description="题目谱系ID"),
    version_number: int = Path(..., description="要恢复的版本号"),
    current_user: dict = Depends(get_current_user),
):
    """恢复某历史版本（基于旧版本创建新版本）"""
    try:
        result = restore_version(
            question_id=question_id,
            user_id=current_user["user_id"],
            target_version_number=version_number,
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.post("/{question_id}/share")
def api_share_question(
    payload: QuestionShareRequest,
    question_id: str = Path(..., description="题目谱系ID"),
    current_user: dict = Depends(get_current_user),
):
    """共享题目"""
    try:
        result = share_question(
            question_id=question_id,
            user_id=current_user["user_id"],
            target_username=payload.username,
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.post("/{question_id}/unshare")
def api_unshare_question(
    payload: QuestionUnshareRequest,
    question_id: str = Path(..., description="题目谱系ID"),
    current_user: dict = Depends(get_current_user),
):
    """取消共享"""
    try:
        result = unshare_question(
            question_id=question_id,
            user_id=current_user["user_id"],
            target_username=payload.username,
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.post("/{question_id}/bank")
def api_add_to_bank(
    question_id: str = Path(..., description="题目谱系ID"),
    current_user: dict = Depends(get_current_user),
):
    """加入题库"""
    try:
        result = add_to_bank(
            question_id=question_id,
            user_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.delete("/{question_id}/bank")
def api_remove_from_bank(
    question_id: str = Path(..., description="题目谱系ID"),
    current_user: dict = Depends(get_current_user),
):
    """移出题库"""
    try:
        result = remove_from_bank(
            question_id=question_id,
            user_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.get("/{question_id}/usage")
def api_get_question_usage(
    question_id: str = Path(..., description="题目谱系ID"),
    current_user: dict = Depends(get_current_user),
):
    """查看题目使用情况"""
    try:
        result = get_question_usage(
            question_id=question_id,
            user_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)


@router.delete("/{question_id}")
def api_delete_question(
    question_id: str = Path(..., description="题目谱系ID"),
    current_user: dict = Depends(get_current_user),
):
    """删除题目"""
    try:
        result = delete_question(
            question_id=question_id,
            user_id=current_user["user_id"],
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(success_response(data=result)),
        )
    except QuestionServiceError as exc:
        return _handle_error(exc)
