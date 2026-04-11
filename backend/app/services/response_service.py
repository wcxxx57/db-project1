"""答卷提交业务逻辑 —— 含跳转逻辑引擎 & 答案校验（第二阶段改造）"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union

from bson import ObjectId
from bson.errors import InvalidId

from app.database import get_db
from app.utils.response import ErrorCodes


class ResponseServiceError(Exception):
    """答卷业务异常，携带业务码与 HTTP 状态码。"""

    def __init__(self, business_code: int, message: str, http_status: int):
        super().__init__(message)
        self.business_code = business_code
        self.message = message
        self.http_status = http_status


def _to_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize datetime to UTC-aware for safe comparison."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ====================================================================
#  解析题目引用 → 完整题目内容
# ====================================================================

def _resolve_survey_questions(survey: Dict[str, Any]) -> List[Dict[str, Any]]:
    """将问卷的引用格式题目解析为包含完整内容的题目列表"""
    db = get_db()
    questions = survey.get("questions", [])
    if not questions:
        return []

    # 收集需要查询的 question_ref_id
    ref_ids = list({q["question_ref_id"] for q in questions if q.get("question_ref_id")})

    question_docs = {}
    if ref_ids:
        try:
            obj_ids = [ObjectId(rid) for rid in ref_ids]
            for d in db.questions.find({"_id": {"$in": obj_ids}}):
                question_docs[str(d["_id"])] = d
        except InvalidId:
            pass

    resolved = []
    for q in questions:
        item = dict(q)
        ref_id = q.get("question_ref_id")
        vn = q.get("version_number")
        doc = question_docs.get(ref_id)
        if doc and vn is not None:
            for v in doc.get("versions", []):
                if v["version_number"] == vn:
                    item["type"] = v.get("type", "")
                    item["title"] = v.get("title", "")
                    item["required"] = v.get("required", True)
                    item["options"] = v.get("options")
                    item["validation"] = v.get("validation")
                    break
        resolved.append(item)
    return resolved


# ====================================================================
#  跳转逻辑引擎
# ====================================================================

def _evaluate_select_option_condition(condition: Dict, answer: Any) -> bool:
    """评估单选匹配条件：answer == 某选项 option_id"""
    target_option = condition.get("option_id")
    return answer == target_option


def _evaluate_contains_option_condition(condition: Dict, answer: Any) -> bool:
    """评估多选包含条件：answer(列表) 包含指定的 option_ids"""
    if not isinstance(answer, list):
        return False

    target_ids = condition.get("option_ids", [])
    match_type = condition.get("match_type", "any")

    if match_type == "all":
        return all(opt_id in answer for opt_id in target_ids)
    else:
        return any(opt_id in answer for opt_id in target_ids)


def _evaluate_number_compare_condition(condition: Dict, answer: Any) -> bool:
    """评估数字比较条件"""
    try:
        num_answer = float(answer)
    except (TypeError, ValueError):
        return False

    operator = condition.get("operator", "eq")
    value = condition.get("value")
    min_val = condition.get("min_value")
    max_val = condition.get("max_value")

    if operator == "eq":
        return num_answer == value
    elif operator == "ne":
        return num_answer != value
    elif operator == "gt":
        return num_answer > value
    elif operator == "gte":
        return num_answer >= value
    elif operator == "lt":
        return num_answer < value
    elif operator == "lte":
        return num_answer <= value
    elif operator == "between":
        if min_val is not None and max_val is not None:
            return min_val <= num_answer <= max_val
        return False

    return False


def evaluate_condition(condition: Dict, answer: Any) -> bool:
    """评估单个跳转条件是否成立"""
    cond_type = condition.get("type", "")

    if cond_type == "select_option":
        return _evaluate_select_option_condition(condition, answer)
    elif cond_type == "contains_option":
        return _evaluate_contains_option_condition(condition, answer)
    elif cond_type == "number_compare":
        return _evaluate_number_compare_condition(condition, answer)

    return False


def compute_jump_target(question: Dict, answer: Any) -> Optional[str]:
    """根据题目的跳转逻辑和用户答案，计算跳转目标"""
    logic = question.get("logic")
    if not logic or not logic.get("enabled"):
        return None

    rules = logic.get("rules", [])

    for rule in rules:
        condition = rule.get("condition", {})
        action = rule.get("action", {})

        if evaluate_condition(condition, answer):
            action_type = action.get("type", "")
            if action_type == "end_survey":
                return "__END__"
            elif action_type == "jump_to":
                return action.get("target_question_id")

    return None


def compute_required_questions(questions: List[Dict], answers_map: Dict[str, Any]) -> List[str]:
    """根据跳转逻辑和用户的答案，计算实际需要回答的题目列表"""
    if not questions:
        return []

    sorted_questions = sorted(questions, key=lambda q: q.get("order", 0))

    qid_to_index = {}
    for i, q in enumerate(sorted_questions):
        qid_to_index[q["question_id"]] = i

    required_qids = []
    current_index = 0

    while current_index < len(sorted_questions):
        q = sorted_questions[current_index]
        qid = q["question_id"]
        required_qids.append(qid)

        answer = answers_map.get(qid)
        jump_target = compute_jump_target(q, answer)

        if jump_target == "__END__":
            break
        elif jump_target is not None and jump_target in qid_to_index:
            target_index = qid_to_index[jump_target]
            if target_index > current_index:
                current_index = target_index
            else:
                current_index += 1
        else:
            current_index += 1

    return required_qids


# ====================================================================
#  答案校验
# ====================================================================

def validate_single_answer(question: Dict, answer: Any) -> Optional[str]:
    """校验单个题目的答案"""
    q_type = question.get("type", "")
    q_title = question.get("title", "")
    validation = question.get("validation") or {}
    options = question.get("options") or []
    option_ids = {opt["option_id"] for opt in options}

    if q_type == "single_choice":
        if not isinstance(answer, str):
            return f"「{q_title}」的答案必须是字符串（选项ID）"
        if answer not in option_ids:
            return f"「{q_title}」选择了不存在的选项：{answer}"

    elif q_type == "multiple_choice":
        if not isinstance(answer, list):
            return f"「{q_title}」的答案必须是数组（选项ID列表）"

        for a in answer:
            if a not in option_ids:
                return f"「{q_title}」选择了不存在的选项：{a}"

        count = len(answer)

        exact = validation.get("exact_selected")
        if exact is not None:
            if count != exact:
                return f"「{q_title}」必须选择 {exact} 项，当前选择了 {count} 项"
        else:
            min_sel = validation.get("min_selected")
            max_sel = validation.get("max_selected")
            if min_sel is not None and count < min_sel:
                return f"「{q_title}」至少选择 {min_sel} 项，当前选择了 {count} 项"
            if max_sel is not None and count > max_sel:
                return f"「{q_title}」最多选择 {max_sel} 项，当前选择了 {count} 项"

    elif q_type == "text_input":
        if not isinstance(answer, str):
            return f"「{q_title}」的答案必须是字符串"

        text_len = len(answer)
        min_len = validation.get("min_length")
        max_len = validation.get("max_length")
        if min_len is not None and text_len < min_len:
            return f"「{q_title}」至少输入 {min_len} 个字，当前 {text_len} 个字"
        if max_len is not None and text_len > max_len:
            return f"「{q_title}」最多输入 {max_len} 个字，当前 {text_len} 个字"

    elif q_type == "number_input":
        if not isinstance(answer, (int, float)):
            return f"「{q_title}」的答案必须是数字"

        integer_only = validation.get("integer_only")
        if integer_only and not isinstance(answer, int) and answer != int(answer):
            return f"「{q_title}」必须为整数"

        min_val = validation.get("min_value")
        max_val = validation.get("max_value")
        if min_val is not None and answer < min_val:
            return f"「{q_title}」的值不能小于 {min_val}"
        if max_val is not None and answer > max_val:
            return f"「{q_title}」的值不能大于 {max_val}"

    return None


# ====================================================================
#  提交答卷
# ====================================================================

def submit_response(
    survey_id: str,
    access_code: str,
    answers: List[Dict[str, Any]],
    respondent_id: Optional[str] = None,
    is_anonymous_choice: Optional[bool] = None,
    completion_time: Optional[int] = None,
) -> Dict[str, Any]:
    """提交答卷（第二阶段：基于解析后的题目版本内容校验，写入时补齐引用信息）"""
    db = get_db()

    # 1. 获取问卷
    try:
        survey = db.surveys.find_one({"_id": ObjectId(survey_id)})
    except Exception:
        raise ResponseServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if survey is None:
        raise ResponseServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    # 2. 验证访问码
    if survey["access_code"] != access_code:
        raise ResponseServiceError(ErrorCodes.INVALID_ACCESS_CODE, "访问码无效", 400)

    # 3. 验证问卷状态
    if survey["status"] != "published":
        raise ResponseServiceError(ErrorCodes.SURVEY_CLOSED, "问卷未发布或已关闭", 400)

    # 4. 验证截止时间
    deadline = _to_utc_aware(survey.get("deadline"))
    if deadline and deadline < datetime.now(timezone.utc):
        raise ResponseServiceError(ErrorCodes.SURVEY_EXPIRED, "问卷已过期", 400)

    # 5. 登录校验
    if respondent_id is None:
        raise ResponseServiceError(
            ErrorCodes.LOGIN_REQUIRED,
            "请先登录后再填写问卷",
            401,
        )

    # 6. 处理匿名逻辑
    settings = survey.get("settings", {})
    allow_anonymous = settings.get("allow_anonymous", True)
    allow_multiple = settings.get("allow_multiple", False)

    if is_anonymous_choice is True and allow_anonymous:
        is_anonymous = True
    else:
        is_anonymous = False

    if is_anonymous_choice is True and not allow_anonymous:
        raise ResponseServiceError(
            ErrorCodes.ANSWER_VALIDATION_FAILED,
            "该问卷不允许匿名填写",
            400,
        )

    # 7. 验证重复提交
    existing_count = db.responses.count_documents({
        "survey_id": ObjectId(survey_id),
        "respondent_id": ObjectId(respondent_id),
    })
    if existing_count > 0 and not allow_multiple:
        raise ResponseServiceError(
            ErrorCodes.DUPLICATE_SUBMISSION,
            "您已经提交过该问卷，不允许重复提交",
            400,
        )

    # 8. 解析题目引用内容
    resolved_questions = _resolve_survey_questions(survey)
    question_map = {q["question_id"]: q for q in resolved_questions}
    answers_map = {a["question_id"]: a["answer"] for a in answers}

    # 9. 根据跳转逻辑计算实际需要回答的题目
    required_qids = compute_required_questions(resolved_questions, answers_map)

    # 10. 校验必填题
    for qid in required_qids:
        q = question_map.get(qid)
        if q is None:
            continue
        if q.get("required", True) and qid not in answers_map:
            raise ResponseServiceError(
                ErrorCodes.REQUIRED_QUESTION_MISSING,
                f"必填题「{q.get('title', qid)}」未回答",
                400,
            )

    # 11. 校验每个答案的值
    for qid in required_qids:
        if qid not in answers_map:
            continue
        q = question_map.get(qid)
        if q is None:
            continue
        error_msg = validate_single_answer(q, answers_map[qid])
        if error_msg:
            raise ResponseServiceError(
                ErrorCodes.ANSWER_VALIDATION_FAILED,
                error_msg,
                400,
            )

    # 12. 构建答卷文档（补齐 question_ref_id 和 version_number）
    now = datetime.now()
    required_set = set(required_qids)
    answer_docs = []
    for a in answers:
        if a["question_id"] not in required_set:
            continue
        q = question_map.get(a["question_id"])
        answer_doc = {
            "question_id": a["question_id"],
            "answer": a["answer"],
        }
        if q:
            answer_doc["question_ref_id"] = q.get("question_ref_id")
            answer_doc["version_number"] = q.get("version_number")
        answer_docs.append(answer_doc)

    response_doc = {
        "survey_id": ObjectId(survey_id),
        "respondent_id": ObjectId(respondent_id),
        "is_anonymous": is_anonymous,
        "submitted_at": now,
        "answers": answer_docs,
        "completion_time": completion_time,
    }

    result = db.responses.insert_one(response_doc)

    # 13. 更新问卷的 response_count
    db.surveys.update_one(
        {"_id": ObjectId(survey_id)},
        {"$inc": {"response_count": 1}},
    )

    return {
        "response_id": str(result.inserted_id),
        "survey_id": survey_id,
        "submitted_at": now,
        "submission_count": existing_count + 1,
    }


# ====================================================================
#  获取答卷列表（创建者使用）
# ====================================================================

def get_response_list(survey_id: str, creator_id: str) -> List[Dict[str, Any]]:
    """获取某问卷的答卷列表（创建者权限），包含填写者信息"""
    db = get_db()

    try:
        survey = db.surveys.find_one({"_id": ObjectId(survey_id)})
    except Exception:
        raise ResponseServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if survey is None:
        raise ResponseServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if str(survey["creator_id"]) != creator_id:
        raise ResponseServiceError(ErrorCodes.NO_PERMISSION, "无权限查看答卷", 403)

    cursor = db.responses.find(
        {"survey_id": ObjectId(survey_id)}
    ).sort("submitted_at", -1)

    docs = list(cursor)
    respondent_ids = list({doc["respondent_id"] for doc in docs if doc.get("respondent_id")})
    user_map: Dict[str, str] = {}
    if respondent_ids:
        users = db.users.find({"_id": {"$in": respondent_ids}})
        for u in users:
            user_map[str(u["_id"])] = u.get("username", "未知用户")

    results = []
    for doc in docs:
        rid = doc.get("respondent_id")
        rid_str = str(rid) if rid else None
        is_anon = doc.get("is_anonymous", True)

        results.append({
            "response_id": str(doc["_id"]),
            "respondent_id": None if is_anon else rid_str,
            "is_anonymous": is_anon,
            "respondent_name": user_map.get(rid_str, "未知用户") if rid_str and not is_anon else None,
            "submitted_at": doc["submitted_at"],
            "completion_time": doc.get("completion_time"),
        })

    return results


def get_response_detail(response_id: str, creator_id: str) -> Dict[str, Any]:
    """获取答卷详情（创建者权限）"""
    db = get_db()

    try:
        doc = db.responses.find_one({"_id": ObjectId(response_id)})
    except Exception:
        raise ResponseServiceError(ErrorCodes.SURVEY_NOT_FOUND, "答卷不存在", 404)

    if doc is None:
        raise ResponseServiceError(ErrorCodes.SURVEY_NOT_FOUND, "答卷不存在", 404)

    survey = db.surveys.find_one({"_id": doc["survey_id"]})
    if survey is None or str(survey["creator_id"]) != creator_id:
        raise ResponseServiceError(ErrorCodes.NO_PERMISSION, "无权限查看该答卷", 403)

    rid = doc.get("respondent_id")
    is_anon = doc.get("is_anonymous", True)
    respondent_name = None
    if rid and not is_anon:
        user = db.users.find_one({"_id": rid})
        if user:
            respondent_name = user.get("username", "未知用户")

    return {
        "response_id": str(doc["_id"]),
        "survey_id": str(doc["survey_id"]),
        "respondent_id": str(rid) if rid else None,
        "is_anonymous": is_anon,
        "respondent_name": respondent_name,
        "submitted_at": doc["submitted_at"],
        "answers": doc.get("answers", []),
        "completion_time": doc.get("completion_time"),
    }
