import secrets
import string
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bson.objectid import ObjectId
from bson.errors import InvalidId

from app.database import get_db
from app.models.survey import SurveyCreateRequest
from app.utils.response import ErrorCodes


def _to_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize datetime to UTC-aware for safe comparison."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SurveyServiceError(Exception):
    def __init__(self, business_code: int, message: str, http_status: int = 400):
        self.business_code = business_code
        self.message = message
        self.http_status = http_status
        super().__init__(message)

def _generate_access_code(length: int = 8) -> str:
    db = get_db()
    alphabet = string.ascii_letters + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(length))
        if not db.surveys.find_one({"access_code": code}):
            return code

def _serialize_survey(doc: Dict[str, Any]) -> Dict[str, Any]:
    """将 MongoDB 文档转换为 API 响应格式"""
    return {
        "survey_id": str(doc["_id"]),
        "title": doc["title"],
        "description": doc.get("description"),
        "creator_id": str(doc["creator_id"]),
        "access_code": doc["access_code"],
        "status": doc["status"],
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
        "deadline": _to_utc_aware(doc.get("deadline")),
        "response_count": doc.get("response_count", 0),
        "settings": doc.get("settings", {"allow_anonymous": True, "allow_multiple": False}),
        "questions": doc.get("questions", []),
    }


def _serialize_survey_list_item(doc: Dict[str, Any]) -> Dict[str, Any]:
    """将 MongoDB 文档转换为列表项格式（不含题目详情）"""
    return {
        "survey_id": str(doc["_id"]),
        "title": doc["title"],
        "description": doc.get("description"),
        "status": doc["status"],
        "created_at": doc["created_at"],
        "deadline": _to_utc_aware(doc.get("deadline")),
        "response_count": doc.get("response_count", 0),
        "access_code": doc["access_code"],
    }

def create_survey(user_id: str, request: SurveyCreateRequest) -> Dict[str, Any]:
    """创建问卷"""
    db = get_db()
    now = datetime.now(timezone.utc)
    access_code = _generate_access_code()

    settings = request.settings.model_dump() if request.settings else {"allow_anonymous": True, "allow_multiple": False}

    survey_doc = {
        "title": request.title,
        "description": request.description,
        "creator_id": ObjectId(user_id),
        "access_code": access_code,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "deadline": _to_utc_aware(request.deadline),
        "response_count": 0,
        "settings": settings,
        "questions": [],
    }

    result = db.surveys.insert_one(survey_doc)
    return {
        "survey_id": str(result.inserted_id),
        "status": "draft",
        "access_code": access_code,
        "created_at": now,
    }

def get_survey_detail(survey_id: str, user_id: str) -> dict:
    db = get_db()
    try:
        obj_id = ObjectId(survey_id)
    except InvalidId:
        raise SurveyServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)
        
    doc = db.surveys.find_one({"_id": obj_id})
    if not doc:
        raise SurveyServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)
        
    if str(doc.get("creator_id")) != user_id:
        raise SurveyServiceError(ErrorCodes.NO_PERMISSION, "无权限操作该问卷", 403)
        
    return _serialize_survey(doc)


def get_my_surveys(user_id: str, page: int = 1, page_size: int = 10) -> dict:
    db = get_db()
    skip = (page - 1) * page_size
    query = {"creator_id": ObjectId(user_id)}
    
    total = db.surveys.count_documents(query)
    cursor = db.surveys.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    
    surveys = [_serialize_survey_list_item(doc) for doc in cursor]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "surveys": surveys
    }

def publish_survey(survey_id: str, user_id: str) -> dict:
    db = get_db()
    survey = get_survey_detail(survey_id, user_id)
    
    if survey["status"] != "published":
        db.surveys.update_one(
            {"_id": ObjectId(survey_id)},
            {"$set": {"status": "published", "updated_at": datetime.now(timezone.utc)}}
        )
        survey["status"] = "published"
        
    return survey


def close_survey(survey_id: str, user_id: str) -> dict:
    db = get_db()
    survey = get_survey_detail(survey_id, user_id)
    
    if survey["status"] != "closed":
        db.surveys.update_one(
            {"_id": ObjectId(survey_id)},
            {"$set": {"status": "closed", "updated_at": datetime.now(timezone.utc)}}
        )
        survey["status"] = "closed"
        
    return survey


def delete_survey(survey_id: str, user_id: str) -> None:
    db = get_db()
    # 鉴权
    get_survey_detail(survey_id, user_id)
    db.responses.delete_many({"survey_id": ObjectId(survey_id)})
    db.surveys.delete_one({"_id": ObjectId(survey_id)})


def _validate_question_validation(question: dict) -> Optional[str]:
    """验证题目的 validation 规则，返回错误信息或 None"""
    validation = question.get("validation")
    if not validation:
        return None
    
    q_type = question.get("type")
    q_title = question.get("title", "未命名题目")
    
    # 多选题验证
    if q_type == "multiple_choice":
        min_sel = validation.get("min_selected")
        max_sel = validation.get("max_selected")
        if min_sel is not None and max_sel is not None and max_sel < min_sel:
            return f"「{q_title}」最多选择项({max_sel})不能小于最少选择项({min_sel})"
    
    # 文本填空验证
    if q_type == "text_input":
        min_len = validation.get("min_length")
        max_len = validation.get("max_length")
        if min_len is not None and max_len is not None and max_len < min_len:
            return f"「{q_title}」最多字数({max_len})不能小于最少字数({min_len})"
    
    # 数字填空验证
    if q_type == "number_input":
        min_val = validation.get("min_value")
        max_val = validation.get("max_value")
        if min_val is not None and max_val is not None and max_val < min_val:
            return f"「{q_title}」最大值({max_val})不能小于最小值({min_val})"
    
    return None


def update_survey(survey_id: str, user_id: str, request) -> Dict[str, Any]:
    """更新问卷（draft 和 closed 状态允许编辑，published 不可编辑）"""
    db = get_db()

    # 鉴权 + 获取当前问卷
    survey = get_survey_detail(survey_id, user_id)

    if survey["status"] == "published":
        raise SurveyServiceError(
            ErrorCodes.NO_PERMISSION,
            "问卷收集中不可编辑，请先关闭问卷",
            403,
        )

    update_fields: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}

    if request.title is not None:
        update_fields["title"] = request.title
    if request.description is not None:
        update_fields["description"] = request.description
    if request.settings is not None:
        update_fields["settings"] = request.settings.model_dump()
    if request.deadline is not None:
        update_fields["deadline"] = _to_utc_aware(request.deadline)
    if request.questions is not None:
        # 验证题目的 validation 规则
        questions_dict = [q.model_dump() for q in request.questions]
        for q in questions_dict:
            error = _validate_question_validation(q)
            if error:
                raise SurveyServiceError(
                    ErrorCodes.INVALID_PARAM,
                    f"题目验证规则错误：{error}",
                    400,
                )
        update_fields["questions"] = questions_dict

    db.surveys.update_one(
        {"_id": ObjectId(survey_id)},
        {"$set": update_fields},
    )

    # 返回更新后的完整问卷
    return get_survey_detail(survey_id, user_id)


def get_public_survey(access_code: str, respondent_id: Optional[str] = None) -> Dict[str, Any]: # 通过访问码获取可填写问卷
    db = get_db()

    doc = db.surveys.find_one({"access_code": access_code})
    if not doc:
        raise SurveyServiceError(ErrorCodes.INVALID_ACCESS_CODE, "访问码无效", 400)

    if doc.get("status") != "published":
        raise SurveyServiceError(ErrorCodes.SURVEY_CLOSED, "问卷未发布或已关闭", 400)

    deadline = _to_utc_aware(doc.get("deadline"))
    if deadline and deadline < datetime.now(timezone.utc):
        raise SurveyServiceError(ErrorCodes.SURVEY_EXPIRED, "问卷已过期", 400)

    settings = doc.get("settings", {"allow_anonymous": True, "allow_multiple": False})
    allow_multiple = bool(settings.get("allow_multiple", False))
    has_submitted = False
    if respondent_id:
        existing_count = db.responses.count_documents(
            {
                "survey_id": doc["_id"],
                "respondent_id": ObjectId(respondent_id),
            }
        )
        has_submitted = existing_count > 0

    return {
        "survey_id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "description": doc.get("description"),
        "access_code": doc.get("access_code"),
        "deadline": deadline,
        "settings": settings,
        "questions": doc.get("questions", []),
        "has_submitted": has_submitted,
        "allow_multiple": allow_multiple,
    }