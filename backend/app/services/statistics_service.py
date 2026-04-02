"""统计分析业务逻辑"""

from typing import Dict, Any, List

from bson import ObjectId

from app.database import get_db
from app.utils.response import ErrorCodes


class StatisticsServiceError(Exception):
    """统计业务异常"""

    def __init__(self, business_code: int, message: str, http_status: int):
        super().__init__(message)
        self.business_code = business_code
        self.message = message
        self.http_status = http_status


def _build_respondent_info(entry: Dict[str, Any], user_map: Dict[str, str]) -> Dict[str, Any]:
    """构建单个答题者展示信息（实名/匿名）。"""
    is_anonymous = bool(entry.get("is_anonymous", True))
    respondent_id = entry.get("respondent_id")

    if is_anonymous or respondent_id is None:
        return {
            "respondent_id": None,
            "display_name": "匿名用户",
            "is_anonymous": True,
        }

    rid_str = str(respondent_id)
    return {
        "respondent_id": rid_str,
        "display_name": user_map.get(rid_str, "未知用户"),
        "is_anonymous": False,
    }


def _build_question_statistic(
    question: Dict,
    all_responses: List[Dict],
    user_map: Dict[str, str],
) -> Dict[str, Any]:
    """构建单个题目的统计结果

    Args:
        question: 题目字典
        all_responses: 该问卷的所有答卷文档列表

    Returns:
        题目统计结果字典
    """
    qid = question["question_id"]
    q_type = question.get("type", "")
    q_title = question.get("title", "")
    options = question.get("options") or []

    # 收集该题的所有答案和答题者信息
    answer_entries: List[Dict[str, Any]] = []
    for resp in all_responses:
        for ans in resp.get("answers", []):
            if ans.get("question_id") == qid:
                answer_entries.append(
                    {
                        "answer": ans.get("answer"),
                        "respondent_id": resp.get("respondent_id"),
                        "is_anonymous": resp.get("is_anonymous", True),
                        "response_id": str(resp.get("_id")),
                    }
                )
                break

    total_answers = len(answer_entries)

    result: Dict[str, Any] = {
        "question_id": qid,
        "title": q_title,
        "type": q_type,
        "total_answers": total_answers,
    }

    # ---- 单选题 / 多选题 ----
    if q_type in ("single_choice", "multiple_choice"):
        option_counts: Dict[str, int] = {}
        option_respondents: Dict[str, List[Dict[str, Any]]] = {}
        option_respondent_seen: Dict[str, set] = {}

        for opt in options:
            option_id = opt["option_id"]
            option_counts[option_id] = 0
            option_respondents[option_id] = []
            option_respondent_seen[option_id] = set()

        def _append_respondent(option_id: str, entry: Dict[str, Any]) -> None:
            respondent = _build_respondent_info(entry, user_map)
            if respondent["is_anonymous"]:
                dedup_key = f"anon:{entry.get('response_id')}"
            else:
                dedup_key = f"real:{respondent['respondent_id']}"
            if dedup_key in option_respondent_seen[option_id]:
                return
            option_respondent_seen[option_id].add(dedup_key)
            option_respondents[option_id].append(respondent)

        for entry in answer_entries:
            answer = entry.get("answer")
            if q_type == "single_choice" and isinstance(answer, str):
                if answer in option_counts:
                    option_counts[answer] += 1
                    _append_respondent(answer, entry)
            elif q_type == "multiple_choice" and isinstance(answer, list):
                for opt_id in answer:
                    if opt_id in option_counts:
                        option_counts[opt_id] += 1
                        _append_respondent(opt_id, entry)

        option_statistics = []
        for opt in options:
            oid = opt["option_id"]
            count = option_counts.get(oid, 0)
            percentage = round((count / total_answers * 100), 2) if total_answers > 0 else 0.0
            option_statistics.append({
                "option_id": oid,
                "text": opt.get("text", ""),
                "count": count,
                "percentage": percentage,
                "respondents": option_respondents.get(oid, []),
            })

        result["option_statistics"] = option_statistics

    # ---- 文本填空 ----
    elif q_type == "text_input":
        text_responses = [entry.get("answer") for entry in answer_entries if isinstance(entry.get("answer"), str)]
        result["text_responses"] = text_responses

    # ---- 数字填空 ----
    elif q_type == "number_input":
        num_values = []
        for entry in answer_entries:
            a = entry.get("answer")
            if isinstance(a, (int, float)):
                num_values.append(a)

        if num_values:
            result["number_statistics"] = {
                "average": round(sum(num_values) / len(num_values), 2),
                "min": min(num_values),
                "max": max(num_values),
                "values": num_values,
            }
        else:
            result["number_statistics"] = {
                "average": 0,
                "min": 0,
                "max": 0,
                "values": [],
            }

    return result


def get_survey_statistics(survey_id: str, creator_id: str) -> Dict[str, Any]:
    """获取问卷整体统计

    Args:
        survey_id: 问卷ID
        creator_id: 当前用户ID（用于权限验证）

    Returns:
        问卷统计结果
    """
    db = get_db()

    # 获取问卷
    try:
        survey = db.surveys.find_one({"_id": ObjectId(survey_id)})
    except Exception:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if survey is None:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if str(survey["creator_id"]) != creator_id:
        raise StatisticsServiceError(ErrorCodes.NO_PERMISSION, "无权限查看统计", 403)

    # 获取所有答卷
    all_responses = list(db.responses.find({"survey_id": ObjectId(survey_id)}))
    total_responses = len(all_responses)

    # 批量获取实名用户名称
    respondent_ids = list(
        {
            doc.get("respondent_id")
            for doc in all_responses
            if doc.get("respondent_id") and not doc.get("is_anonymous", True)
        }
    )
    user_map: Dict[str, str] = {}
    if respondent_ids:
        users = db.users.find({"_id": {"$in": respondent_ids}})
        for user in users:
            user_map[str(user["_id"])] = user.get("username", "未知用户")

    # 构建各题统计
    questions = survey.get("questions", [])
    question_statistics = []
    for q in questions:
        stat = _build_question_statistic(q, all_responses, user_map)
        question_statistics.append(stat)

    return {
        "survey_id": survey_id,
        "survey_title": survey["title"],
        "total_responses": total_responses,
        "question_statistics": question_statistics,
    }


def get_question_statistics(
    survey_id: str,
    question_id: str,
    creator_id: str,
) -> Dict[str, Any]:
    """获取单个题目的统计

    Args:
        survey_id: 问卷ID
        question_id: 题目ID
        creator_id: 当前用户ID

    Returns:
        单题统计结果
    """
    db = get_db()

    # 获取问卷
    try:
        survey = db.surveys.find_one({"_id": ObjectId(survey_id)})
    except Exception:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if survey is None:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if str(survey["creator_id"]) != creator_id:
        raise StatisticsServiceError(ErrorCodes.NO_PERMISSION, "无权限查看统计", 403)

    # 查找目标题目
    questions = survey.get("questions", [])
    target_question = None
    for q in questions:
        if q["question_id"] == question_id:
            target_question = q
            break

    if target_question is None:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "题目不存在", 404)

    # 获取所有答卷
    all_responses = list(db.responses.find({"survey_id": ObjectId(survey_id)}))

    respondent_ids = list(
        {
            doc.get("respondent_id")
            for doc in all_responses
            if doc.get("respondent_id") and not doc.get("is_anonymous", True)
        }
    )
    user_map: Dict[str, str] = {}
    if respondent_ids:
        users = db.users.find({"_id": {"$in": respondent_ids}})
        for user in users:
            user_map[str(user["_id"])] = user.get("username", "未知用户")

    stat = _build_question_statistic(target_question, all_responses, user_map)
    stat["survey_id"] = survey_id

    return stat
