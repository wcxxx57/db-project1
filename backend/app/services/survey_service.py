"""问卷服务模块"""

from datetime import datetime
import secrets
import string
from bson.objectid import ObjectId
from bson.errors import InvalidId

from app.database import get_db
from app.models.survey import SurveyCreateRequest
from app.utils.response import ErrorCodes


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


def _format_survey(doc: dict) -> dict:
    if not doc:
        return doc
    doc["survey_id"] = str(doc.pop("_id"))
    return doc


def create_survey(user_id: str, request: SurveyCreateRequest) -> dict:
    db = get_db()
    access_code = _generate_access_code()
    
    settings = request.settings.model_dump() if request.settings else {"allow_anonymous": True, "allow_multiple": False}
    
    survey_doc = {
        "title": request.title,
        "description": request.description,
        "creator_id": user_id,
        "access_code": access_code,
        "status": "draft",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "deadline": request.deadline,
        "response_count": 0,
        "settings": settings,
        "questions": []
    }
    
    result = db.surveys.insert_one(survey_doc)
    doc = db.surveys.find_one({"_id": result.inserted_id})
    return _format_survey(doc)


def get_survey(survey_id: str, user_id: str) -> dict:
    db = get_db()
    try:
        obj_id = ObjectId(survey_id)
    except InvalidId:
        raise SurveyServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)
        
    doc = db.surveys.find_one({"_id": obj_id})
    if not doc:
        raise SurveyServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)
        
    if doc.get("creator_id") != user_id:
        raise SurveyServiceError(ErrorCodes.NO_PERMISSION, "无权限操作该问卷", 403)
        
    return _format_survey(doc)


def get_user_surveys(user_id: str, page: int = 1, page_size: int = 10) -> dict:
    db = get_db()
    skip = (page - 1) * page_size
    query = {"creator_id": user_id}
    
    total = db.surveys.count_documents(query)
    cursor = db.surveys.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    
    surveys = [_format_survey(doc) for doc in cursor]
        
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "surveys": surveys
    }


def publish_survey(survey_id: str, user_id: str) -> dict:
    db = get_db()
    survey = get_survey(survey_id, user_id)
    
    if survey["status"] != "published":
        db.surveys.update_one(
            {"_id": ObjectId(survey_id)},
            {"$set": {"status": "published", "updated_at": datetime.utcnow()}}
        )
        survey["status"] = "published"
        
    return survey


def close_survey(survey_id: str, user_id: str) -> dict:
    db = get_db()
    survey = get_survey(survey_id, user_id)
    
    if survey["status"] != "closed":
        db.surveys.update_one(
            {"_id": ObjectId(survey_id)},
            {"$set": {"status": "closed", "updated_at": datetime.utcnow()}}
        )
        survey["status"] = "closed"
        
    return survey


def delete_survey(survey_id: str, user_id: str) -> None:
    db = get_db()
    # 鉴权
    get_survey(survey_id, user_id)
    db.surveys.delete_one({"_id": ObjectId(survey_id)})
