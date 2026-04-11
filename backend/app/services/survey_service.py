import secrets
import string
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
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


def _resolve_question_refs(questions: list) -> list:
    """批量解析问卷中的题目引用，补全题目版本内容用于前端展示。

    输入：问卷的 questions 数组（引用格式）
    输出：每个引用项 + 解析后的题目内容字段
    """
    db = get_db()
    if not questions:
        return []

    # 收集需要查询的 question_ref_id
    ref_ids = list({q["question_ref_id"] for q in questions if q.get("question_ref_id")})
    if not ref_ids:
        return questions

    # 批量查询题目文档
    try:
        obj_ids = [ObjectId(rid) for rid in ref_ids]
    except InvalidId:
        return questions
    docs = {str(d["_id"]): d for d in db.questions.find({"_id": {"$in": obj_ids}})}

    resolved = []
    for q in questions:
        item = dict(q)
        ref_id = q.get("question_ref_id")
        vn = q.get("version_number")
        doc = docs.get(ref_id)
        if doc and vn is not None:
            for v in doc.get("versions", []):
                if v["version_number"] == vn:
                    item["type"] = v.get("type", "")
                    item["title"] = v.get("title", "")
                    item["options"] = v.get("options")
                    item["validation"] = v.get("validation")
                    break
        resolved.append(item)
    return resolved


def _serialize_survey(doc: Dict[str, Any], resolve_refs: bool = True) -> Dict[str, Any]:
    """将 MongoDB 文档转换为 API 响应格式"""
    questions = doc.get("questions", [])
    if resolve_refs:
        questions = _resolve_question_refs(questions)
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
        "questions": questions,
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
    now = datetime.now()
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
            {"$set": {"status": "published", "updated_at": datetime.now()}}
        )
        survey["status"] = "published"

    return survey


def close_survey(survey_id: str, user_id: str) -> dict:
    db = get_db()
    survey = get_survey_detail(survey_id, user_id)

    if survey["status"] != "closed":
        db.surveys.update_one(
            {"_id": ObjectId(survey_id)},
            {"$set": {"status": "closed", "updated_at": datetime.now()}}
        )
        survey["status"] = "closed"

    return survey


def delete_survey(survey_id: str, user_id: str) -> None:
    db = get_db()
    # 鉴权
    get_survey_detail(survey_id, user_id)
    db.responses.delete_many({"survey_id": ObjectId(survey_id)})
    db.surveys.delete_one({"_id": ObjectId(survey_id)})


def _validate_question_refs(questions_dict: list, user_id: str) -> Optional[str]:
    """验证题目引用列表：检查 question_ref_id + version_number 存在且用户有权限"""
    db = get_db()

    ref_ids = list({q["question_ref_id"] for q in questions_dict if q.get("question_ref_id")})
    if not ref_ids:
        return None

    try:
        obj_ids = [ObjectId(rid) for rid in ref_ids]
    except InvalidId:
        return "题目引用 ID 格式无效"

    docs = {str(d["_id"]): d for d in db.questions.find({"_id": {"$in": obj_ids}})}

    for q in questions_dict:
        ref_id = q.get("question_ref_id")
        vn = q.get("version_number")
        if not ref_id or vn is None:
            return f"题目引用缺少 question_ref_id 或 version_number"

        doc = docs.get(ref_id)
        if not doc:
            return f"引用的题目 {ref_id} 不存在"

        # 权限校验：创建者或被共享者
        ac = doc.get("access_control", {})
        if ac.get("creator") != user_id and user_id not in ac.get("shared_with", []):
            return f"无权使用题目 {ref_id}"

        # 版本校验
        found = False
        for v in doc.get("versions", []):
            if v["version_number"] == vn:
                found = True
                break
        if not found:
            return f"题目 {ref_id} 的版本 {vn} 不存在"

    return None


def _validate_jump_logic_refs(questions_dict: list) -> Optional[str]:
    """验证引用格式下的跳转逻辑"""
    if not questions_dict:
        return None

    qid_set = {q["question_id"] for q in questions_dict}
    qid_to_order = {q["question_id"]: q.get("order", 0) for q in questions_dict}

    for q in questions_dict:
        logic = q.get("logic")
        if not logic or not logic.get("enabled"):
            continue

        rules = logic.get("rules", [])
        for rule in rules:
            action = rule.get("action", {})
            if action.get("type") == "jump_to":
                target = action.get("target_question_id")
                if target and target not in qid_set:
                    return f"题目「{q['question_id']}」的跳转目标「{target}」不存在"
                if target and qid_to_order.get(target, 0) <= qid_to_order.get(q["question_id"], 0):
                    return f"题目「{q['question_id']}」不允许向前跳转到「{target}」"

    # 循环检测
    def has_cycle(start_qid: str, visited: set) -> bool:
        if start_qid in visited:
            return True
        visited.add(start_qid)
        q = next((q for q in questions_dict if q["question_id"] == start_qid), None)
        if not q:
            return False
        logic = q.get("logic")
        if not logic or not logic.get("enabled"):
            return False
        for rule in logic.get("rules", []):
            action = rule.get("action", {})
            if action.get("type") == "jump_to":
                target = action.get("target_question_id")
                if target and has_cycle(target, visited.copy()):
                    return True
        return False

    for q in questions_dict:
        if has_cycle(q["question_id"], set()):
            return f"检测到循环跳转，涉及题目「{q['question_id']}」"

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

    update_fields: Dict[str, Any] = {"updated_at": datetime.now()}

    if request.title is not None:
        update_fields["title"] = request.title
    if request.description is not None:
        update_fields["description"] = request.description
    if request.settings is not None:
        update_fields["settings"] = request.settings.model_dump()
    if request.deadline is not None:
        update_fields["deadline"] = _to_utc_aware(request.deadline)
    if request.questions is not None:
        questions_dict = [q.model_dump() for q in request.questions]

        # 验证题目引用合法性
        error = _validate_question_refs(questions_dict, user_id)
        if error:
            raise SurveyServiceError(
                ErrorCodes.ANSWER_VALIDATION_FAILED,
                f"题目引用校验失败：{error}",
                400,
            )

        # 验证跳转逻辑
        error = _validate_jump_logic_refs(questions_dict)
        if error:
            raise SurveyServiceError(
                ErrorCodes.ANSWER_VALIDATION_FAILED,
                f"跳转逻辑错误：{error}",
                400,
            )

        update_fields["questions"] = questions_dict

    db.surveys.update_one(
        {"_id": ObjectId(survey_id)},
        {"$set": update_fields},
    )

    # 返回更新后的完整问卷
    return get_survey_detail(survey_id, user_id)


def get_public_survey(access_code: str, respondent_id: Optional[str] = None) -> Dict[str, Any]:
    """通过访问码获取可填写问卷"""
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

    # 解析题目引用内容，前端填写端不感知引用细节
    questions = _resolve_question_refs(doc.get("questions", []))

    return {
        "survey_id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "description": doc.get("description"),
        "access_code": doc.get("access_code"),
        "deadline": deadline,
        "settings": settings,
        "questions": questions,
        "has_submitted": has_submitted,
        "allow_multiple": allow_multiple,
    }
