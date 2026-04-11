"""题目域业务逻辑（第二阶段新增）"""

from datetime import datetime
from typing import Dict, Any, Optional, List

from bson import ObjectId
from bson.errors import InvalidId

from app.database import get_db
from app.utils.response import ErrorCodes


class QuestionServiceError(Exception):
    def __init__(self, business_code: int, message: str, http_status: int = 400):
        self.business_code = business_code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _resolve_usernames(user_ids: List[str]) -> Dict[str, str]:
    """批量将 user_id 列表解析为 {user_id: username} 映射"""
    if not user_ids:
        return {}
    db = get_db()
    obj_ids = []
    for uid in user_ids:
        try:
            obj_ids.append(ObjectId(uid))
        except InvalidId:
            pass
    if not obj_ids:
        return {}
    docs = db.users.find({"_id": {"$in": obj_ids}}, {"username": 1})
    return {str(d["_id"]): d["username"] for d in docs}


def _serialize_question_list_item(doc: Dict[str, Any]) -> Dict[str, Any]:
    """将 MongoDB 文档转换为题目列表项"""
    versions = doc.get("versions", [])
    latest = versions[-1] if versions else {}
    creator_id = doc.get("access_control", {}).get("creator", "")
    name_map = _resolve_usernames([creator_id]) if creator_id else {}
    return {
        "question_id": str(doc["_id"]),
        "latest_version_number": doc.get("latest_version_number", 1),
        "creator": name_map.get(creator_id, creator_id),
        "latest_title": latest.get("title", ""),
        "latest_type": latest.get("type", ""),
        "created_at": versions[0].get("created_at") if versions else None,
    }


def _serialize_question_detail(doc: Dict[str, Any]) -> Dict[str, Any]:
    """将 MongoDB 文档转换为题目详情"""
    ac = doc.get("access_control", {})
    versions = doc.get("versions", [])

    # 收集所有需要解析的 user_id
    all_uids = set()
    creator_id = ac.get("creator", "")
    if creator_id:
        all_uids.add(creator_id)
    for uid in ac.get("shared_with", []):
        all_uids.add(uid)
    for v in versions:
        ub = v.get("updated_by", "")
        if ub:
            all_uids.add(ub)
    name_map = _resolve_usernames(list(all_uids))

    serialized_versions = []
    for v in versions:
        ub = v.get("updated_by", "")
        serialized_versions.append({
            "version_number": v.get("version_number"),
            "created_at": v.get("created_at"),
            "updated_by": name_map.get(ub, ub),
            "parent_version_number": v.get("parent_version_number"),
            "type": v.get("type", ""),
            "title": v.get("title", ""),
            "options": v.get("options"),
            "validation": v.get("validation"),
        })
    return {
        "question_id": str(doc["_id"]),
        "latest_version_number": doc.get("latest_version_number", 1),
        "creator": name_map.get(creator_id, creator_id),
        "shared_with": [name_map.get(uid, uid) for uid in ac.get("shared_with", [])],
        "banked_by": ac.get("banked_by", []),
        "versions": serialized_versions,
    }


def _get_question_doc(question_id: str) -> Dict[str, Any]:
    """获取题目文档，不存在则抛异常"""
    db = get_db()
    try:
        obj_id = ObjectId(question_id)
    except InvalidId:
        raise QuestionServiceError(ErrorCodes.QUESTION_NOT_FOUND, "题目不存在", 404)
    doc = db.questions.find_one({"_id": obj_id})
    if not doc:
        raise QuestionServiceError(ErrorCodes.QUESTION_NOT_FOUND, "题目不存在", 404)
    return doc


def _check_access(doc: Dict[str, Any], user_id: str) -> None:
    """检查用户是否有权访问该题目（创建者或被共享者）"""
    ac = doc.get("access_control", {})
    if ac.get("creator") == user_id:
        return
    if user_id in ac.get("shared_with", []):
        return
    raise QuestionServiceError(ErrorCodes.NO_PERMISSION, "无权限操作该题目", 403)


def create_question(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """创建题目（自动生成 v1）"""
    db = get_db()
    now = datetime.now()

    version_obj = {
        "version_number": 1,
        "created_at": now,
        "updated_by": user_id,
        "parent_version_number": None,
        "type": data["type"],
        "title": data["title"],
        "options": data.get("options"),
        "validation": data.get("validation"),
    }

    question_doc = {
        "latest_version_number": 1,
        "access_control": {
            "creator": user_id,
            "shared_with": [],
            "banked_by": [],
        },
        "versions": [version_obj],
    }

    result = db.questions.insert_one(question_doc)
    return {
        "question_id": str(result.inserted_id),
        "version_number": 1,
        "created_at": now,
    }


def get_my_questions(user_id: str) -> List[Dict[str, Any]]:
    """查询我创建的题目"""
    db = get_db()
    cursor = db.questions.find({"access_control.creator": user_id})
    return [_serialize_question_list_item(doc) for doc in cursor]


def get_shared_questions(user_id: str) -> List[Dict[str, Any]]:
    """查询共享给我的题目"""
    db = get_db()
    cursor = db.questions.find({"access_control.shared_with": user_id})
    return [_serialize_question_list_item(doc) for doc in cursor]


def get_banked_questions(user_id: str) -> List[Dict[str, Any]]:
    """查询我的题库题目"""
    db = get_db()
    cursor = db.questions.find({"access_control.banked_by": user_id})
    return [_serialize_question_list_item(doc) for doc in cursor]


def get_question_detail(question_id: str, user_id: str) -> Dict[str, Any]:
    """查询题目详情"""
    doc = _get_question_doc(question_id)
    _check_access(doc, user_id)
    return _serialize_question_detail(doc)


def create_new_version(question_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """创建题目新版本"""
    db = get_db()
    doc = _get_question_doc(question_id)
    _check_access(doc, user_id)

    parent_version_number = data.get("parent_version_number")

    # 如果指定了 parent_version_number，验证其存在
    if parent_version_number is not None:
        versions = doc.get("versions", [])
        if not any(v["version_number"] == parent_version_number for v in versions):
            raise QuestionServiceError(
                ErrorCodes.QUESTION_VERSION_NOT_FOUND,
                f"版本 {parent_version_number} 不存在",
                404,
            )

    now = datetime.now()
    new_version_number = doc["latest_version_number"] + 1

    version_obj = {
        "version_number": new_version_number,
        "created_at": now,
        "updated_by": user_id,
        "parent_version_number": parent_version_number,
        "type": data["type"],
        "title": data["title"],
        "options": data.get("options"),
        "validation": data.get("validation"),
    }

    # 原子操作：$inc + $push
    db.questions.update_one(
        {"_id": ObjectId(question_id)},
        {
            "$inc": {"latest_version_number": 1},
            "$push": {"versions": version_obj},
        },
    )

    return {
        "question_id": question_id,
        "version_number": new_version_number,
        "created_at": now,
    }


def update_version(question_id: str, user_id: str, version_number: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """原地更新指定版本内容（仅当该版本未被已发布/已关闭问卷使用时允许）"""
    db = get_db()
    doc = _get_question_doc(question_id)
    _check_access(doc, user_id)

    # 验证版本存在
    versions = doc.get("versions", [])
    target_version = None
    target_idx = None
    for idx, v in enumerate(versions):
        if v["version_number"] == version_number:
            target_version = v
            target_idx = idx
            break

    if target_version is None:
        raise QuestionServiceError(
            ErrorCodes.QUESTION_VERSION_NOT_FOUND,
            f"版本 {version_number} 不存在",
            404,
        )

    # 安全检查：查找引用了该版本的已发布/已关闭问卷
    protected_surveys = list(db.surveys.find({
        "questions": {
            "$elemMatch": {
                "question_ref_id": question_id,
                "version_number": version_number,
            }
        },
        "status": {"$in": ["published", "closed"]},
    }, {"_id": 1, "title": 1, "status": 1}))

    if protected_surveys:
        survey_names = [s.get("title", "未命名") for s in protected_surveys]
        raise QuestionServiceError(
            ErrorCodes.NO_PERMISSION,
            f"该版本正在被 {len(protected_surveys)} 份已发布/已关闭的问卷使用（{', '.join(survey_names[:3])}），"
            f"不能直接修改，请创建新版本",
            403,
        )

    # 原地更新版本内容
    now = datetime.now()
    update_fields = {
        f"versions.{target_idx}.type": data["type"],
        f"versions.{target_idx}.title": data["title"],
        f"versions.{target_idx}.options": data.get("options"),
        f"versions.{target_idx}.validation": data.get("validation"),
        f"versions.{target_idx}.updated_by": user_id,
        f"versions.{target_idx}.created_at": now,
    }

    db.questions.update_one(
        {"_id": ObjectId(question_id)},
        {"$set": update_fields},
    )

    return {
        "question_id": question_id,
        "version_number": version_number,
        "updated_at": now,
        "mode": "in_place",
    }


def get_version_history(question_id: str, user_id: str) -> List[Dict[str, Any]]:
    """查询题目版本历史"""
    doc = _get_question_doc(question_id)
    _check_access(doc, user_id)
    versions = doc.get("versions", [])
    return [
        {
            "version_number": v.get("version_number"),
            "created_at": v.get("created_at"),
            "updated_by": v.get("updated_by", ""),
            "parent_version_number": v.get("parent_version_number"),
            "title": v.get("title", ""),
            "type": v.get("type", ""),
        }
        for v in versions
    ]


def restore_version(question_id: str, user_id: str, target_version_number: int) -> Dict[str, Any]:
    """恢复某历史版本（基于目标旧版本内容创建新版本）"""
    doc = _get_question_doc(question_id)
    _check_access(doc, user_id)

    versions = doc.get("versions", [])
    target_version = None
    for v in versions:
        if v["version_number"] == target_version_number:
            target_version = v
            break

    if target_version is None:
        raise QuestionServiceError(
            ErrorCodes.QUESTION_VERSION_NOT_FOUND,
            f"版本 {target_version_number} 不存在",
            404,
        )

    # 基于目标版本内容创建新版本
    return create_new_version(question_id, user_id, {
        "type": target_version["type"],
        "title": target_version["title"],
        "options": target_version.get("options"),
        "validation": target_version.get("validation"),
        "parent_version_number": target_version_number,
    })


def share_question(question_id: str, user_id: str, target_username: str) -> Dict[str, Any]:
    """共享题目给指定用户"""
    db = get_db()
    doc = _get_question_doc(question_id)

    # 仅创建者可以共享
    ac = doc.get("access_control", {})
    if ac.get("creator") != user_id:
        raise QuestionServiceError(ErrorCodes.NO_PERMISSION, "仅题目创建者可以共享", 403)

    # 查找目标用户
    target_user = db.users.find_one({"username": target_username})
    if not target_user:
        raise QuestionServiceError(ErrorCodes.SHARE_TARGET_NOT_FOUND, f"用户「{target_username}」不存在", 404)

    target_user_id = str(target_user["_id"])
    if target_user_id == user_id:
        raise QuestionServiceError(ErrorCodes.ANSWER_VALIDATION_FAILED, "不能共享给自己", 400)

    # $addToSet 避免重复
    db.questions.update_one(
        {"_id": ObjectId(question_id)},
        {"$addToSet": {"access_control.shared_with": target_user_id}},
    )

    return {"message": f"已共享给用户「{target_username}」"}


def unshare_question(question_id: str, user_id: str, target_username: str) -> Dict[str, Any]:
    """取消共享"""
    db = get_db()
    doc = _get_question_doc(question_id)

    ac = doc.get("access_control", {})
    if ac.get("creator") != user_id:
        raise QuestionServiceError(ErrorCodes.NO_PERMISSION, "仅题目创建者可以取消共享", 403)

    target_user = db.users.find_one({"username": target_username})
    if not target_user:
        raise QuestionServiceError(ErrorCodes.SHARE_TARGET_NOT_FOUND, f"用户「{target_username}」不存在", 404)

    target_user_id = str(target_user["_id"])

    db.questions.update_one(
        {"_id": ObjectId(question_id)},
        {"$pull": {"access_control.shared_with": target_user_id}},
    )

    return {"message": f"已取消共享给用户「{target_username}」"}


def add_to_bank(question_id: str, user_id: str) -> Dict[str, Any]:
    """加入题库"""
    db = get_db()
    doc = _get_question_doc(question_id)
    _check_access(doc, user_id)

    db.questions.update_one(
        {"_id": ObjectId(question_id)},
        {"$addToSet": {"access_control.banked_by": user_id}},
    )

    return {"message": "已加入题库"}


def remove_from_bank(question_id: str, user_id: str) -> Dict[str, Any]:
    """移出题库"""
    db = get_db()
    doc = _get_question_doc(question_id)
    _check_access(doc, user_id)

    db.questions.update_one(
        {"_id": ObjectId(question_id)},
        {"$pull": {"access_control.banked_by": user_id}},
    )

    return {"message": "已移出题库"}


def get_question_usage(question_id: str, user_id: str) -> List[Dict[str, Any]]:
    """查询题目使用情况（被哪些问卷使用）"""
    db = get_db()
    doc = _get_question_doc(question_id)
    _check_access(doc, user_id)

    # 查找引用了该题目的所有问卷
    surveys = db.surveys.find({"questions.question_ref_id": question_id})

    usage = []
    for s in surveys:
        # 找出该问卷中引用该题目的版本号
        version_numbers = []
        for q in s.get("questions", []):
            if q.get("question_ref_id") == question_id:
                version_numbers.append(q.get("version_number"))
        for vn in version_numbers:
            usage.append({
                "survey_id": str(s["_id"]),
                "survey_title": s.get("title", ""),
                "survey_status": s.get("status", ""),
                "version_number": vn,
            })

    return usage


def delete_question(question_id: str, user_id: str) -> Dict[str, Any]:
    """删除题目（仅创建者；被已发布/已关闭问卷引用时禁止删除）"""
    db = get_db()
    doc = _get_question_doc(question_id)

    ac = doc.get("access_control", {})
    if ac.get("creator") != user_id:
        raise QuestionServiceError(ErrorCodes.NO_PERMISSION, "仅题目创建者可以删除", 403)

    # 查找所有引用该题目的问卷
    affected_surveys = list(db.surveys.find(
        {"questions.question_ref_id": question_id},
        {"_id": 1, "title": 1, "status": 1, "questions": 1},
    ))

    # 若存在已发布/已关闭问卷引用，则禁止删除
    protected = [
        s for s in affected_surveys
        if s.get("status") in {"published", "closed"}
    ]
    if protected:
        survey_names = [s.get("title", "未命名") for s in protected]
        raise QuestionServiceError(
            ErrorCodes.QUESTION_IN_USE,
            f"题目正在被 {len(protected)} 份已发布/已关闭问卷使用（{', '.join(survey_names[:3])}），无法删除",
            400,
        )

    # 仅从草稿问卷中移除题目引用
    for s in affected_surveys:
        # 移除引用该题目的所有条目
        new_questions = [q for q in s.get("questions", []) if q.get("question_ref_id") != question_id]
        # 重新编排 order
        for i, q in enumerate(new_questions):
            q["order"] = i + 1
        db.surveys.update_one(
            {"_id": s["_id"]},
            {"$set": {"questions": new_questions}},
        )

    db.questions.delete_one({"_id": ObjectId(question_id)})

    return {
        "affected_surveys": [
            {"survey_id": str(s["_id"]), "survey_title": s.get("title", "")}
            for s in affected_surveys
        ],
    }


def get_question_version_content(question_id: str, version_number: int) -> Optional[Dict[str, Any]]:
    """获取题目某个版本的内容（内部使用，不做权限校验）"""
    db = get_db()
    try:
        doc = db.questions.find_one({"_id": ObjectId(question_id)})
    except InvalidId:
        return None
    if not doc:
        return None
    for v in doc.get("versions", []):
        if v["version_number"] == version_number:
            return {
                "type": v.get("type", ""),
                "title": v.get("title", ""),
                "options": v.get("options"),
                "validation": v.get("validation"),
            }
    return None
