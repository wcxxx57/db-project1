"""统计分析业务逻辑（第二阶段改造）"""

from typing import Dict, Any, List

from bson import ObjectId
from bson.errors import InvalidId

from app.database import get_db
from app.utils.response import ErrorCodes


class StatisticsServiceError(Exception):
    """统计业务异常"""

    def __init__(self, business_code: int, message: str, http_status: int):
        super().__init__(message)
        self.business_code = business_code
        self.message = message
        self.http_status = http_status


def _resolve_survey_questions(survey: Dict[str, Any]) -> list:
    """将问卷的引用格式题目解析为包含完整内容的题目列表"""
    db = get_db()
    questions = survey.get("questions", [])
    if not questions:
        return []

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
    """构建单个题目的统计结果"""
    qid = question["question_id"]
    q_type = question.get("type", "")
    q_title = question.get("title", "")
    options = question.get("options") or []

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

    if q_type in ("single_choice", "multiple_choice"):
        option_counts: Dict[str, int] = {}
        option_respondents: Dict[str, List[Dict[str, Any]]] = {}
        option_respondent_seen: Dict[str, set] = {}
        unknown_option_count = 0

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
                else:
                    unknown_option_count += 1
            elif q_type == "multiple_choice" and isinstance(answer, list):
                for opt_id in answer:
                    if opt_id in option_counts:
                        option_counts[opt_id] += 1
                        _append_respondent(opt_id, entry)
                    else:
                        unknown_option_count += 1

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

        if unknown_option_count > 0:
            result["warning"] = f"有 {unknown_option_count} 个答案的选项在当前题目定义中已不存在（可能是历史数据）"

    elif q_type == "text_input":
        text_responses = [entry.get("answer") for entry in answer_entries if isinstance(entry.get("answer"), str)]
        result["text_responses"] = text_responses

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


def _get_user_map(db, all_responses: List[Dict]) -> Dict[str, str]:
    """批量获取实名用户名称"""
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
    return user_map


def get_survey_statistics(survey_id: str, creator_id: str) -> Dict[str, Any]:
    """获取问卷整体统计（第二阶段：基于解析后的题目版本内容）"""
    db = get_db()

    try:
        survey = db.surveys.find_one({"_id": ObjectId(survey_id)})
    except Exception:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if survey is None:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if str(survey["creator_id"]) != creator_id:
        raise StatisticsServiceError(ErrorCodes.NO_PERMISSION, "无权限查看统计", 403)

    all_responses = list(db.responses.find({"survey_id": ObjectId(survey_id)}))
    total_responses = len(all_responses)

    user_map = _get_user_map(db, all_responses)

    # 解析题目引用
    resolved_questions = _resolve_survey_questions(survey)
    question_statistics = []
    for q in resolved_questions:
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
    """获取单个题目的统计（第二阶段：基于解析后的题目版本内容）"""
    db = get_db()

    try:
        survey = db.surveys.find_one({"_id": ObjectId(survey_id)})
    except Exception:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if survey is None:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "问卷不存在", 404)

    if str(survey["creator_id"]) != creator_id:
        raise StatisticsServiceError(ErrorCodes.NO_PERMISSION, "无权限查看统计", 403)

    resolved_questions = _resolve_survey_questions(survey)
    target_question = None
    for q in resolved_questions:
        if q["question_id"] == question_id:
            target_question = q
            break

    if target_question is None:
        raise StatisticsServiceError(ErrorCodes.SURVEY_NOT_FOUND, "题目不存在", 404)

    all_responses = list(db.responses.find({"survey_id": ObjectId(survey_id)}))
    user_map = _get_user_map(db, all_responses)

    stat = _build_question_statistic(target_question, all_responses, user_map)
    stat["survey_id"] = survey_id

    return stat


# ====================================================================
#  跨问卷单题统计（第二阶段新增）
# ====================================================================

def get_cross_survey_question_statistics(
    question_ref_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """按题目谱系聚合跨问卷统计，按 version_number 分组展示"""
    db = get_db()

    # 验证题目存在且用户有权限
    try:
        question_doc = db.questions.find_one({"_id": ObjectId(question_ref_id)})
    except InvalidId:
        raise StatisticsServiceError(ErrorCodes.QUESTION_NOT_FOUND, "题目不存在", 404)

    if question_doc is None:
        raise StatisticsServiceError(ErrorCodes.QUESTION_NOT_FOUND, "题目不存在", 404)

    ac = question_doc.get("access_control", {})
    if ac.get("creator") != user_id and user_id not in ac.get("shared_with", []):
        raise StatisticsServiceError(ErrorCodes.NO_PERMISSION, "无权限查看该题目统计", 403)

    # 查找所有包含该题目回答的答卷
    all_responses = list(db.responses.find({"answers.question_ref_id": question_ref_id}))

    # 收集涉及的问卷 ID
    survey_ids = list({resp["survey_id"] for resp in all_responses})
    survey_docs = {}
    if survey_ids:
        for s in db.surveys.find({"_id": {"$in": survey_ids}}):
            survey_docs[str(s["_id"])] = s

    # 按 version_number 分组收集答案
    version_answers: Dict[int, List[Any]] = {}
    version_survey_ids: Dict[int, set] = {}
    total_answers = 0

    for resp in all_responses:
        for ans in resp.get("answers", []):
            if ans.get("question_ref_id") == question_ref_id:
                vn = ans.get("version_number", 1)
                if vn not in version_answers:
                    version_answers[vn] = []
                    version_survey_ids[vn] = set()
                version_answers[vn].append(ans.get("answer"))
                version_survey_ids[vn].add(str(resp["survey_id"]))
                total_answers += 1

    # 获取最新版本信息用于展示
    versions = question_doc.get("versions", [])
    latest = versions[-1] if versions else {}

    # 构建版本分组统计
    version_statistics = []
    for vn in sorted(version_answers.keys()):
        # 找到该版本的内容
        version_content = {}
        for v in versions:
            if v["version_number"] == vn:
                version_content = v
                break

        answers_list = version_answers[vn]
        stat = {
            "version_number": vn,
            "title": version_content.get("title", latest.get("title", "")),
            "type": version_content.get("type", latest.get("type", "")),
            "total_answers": len(answers_list),
            "survey_count": len(version_survey_ids[vn]),
        }

        q_type = version_content.get("type", "")
        options = version_content.get("options") or []

        if q_type in ("single_choice", "multiple_choice"):
            option_counts = {opt["option_id"]: 0 for opt in options}
            for a in answers_list:
                if q_type == "single_choice" and isinstance(a, str):
                    if a in option_counts:
                        option_counts[a] += 1
                elif q_type == "multiple_choice" and isinstance(a, list):
                    for opt_id in a:
                        if opt_id in option_counts:
                            option_counts[opt_id] += 1

            option_statistics = []
            total = len(answers_list)
            for opt in options:
                oid = opt["option_id"]
                count = option_counts.get(oid, 0)
                percentage = round((count / total * 100), 2) if total > 0 else 0.0
                option_statistics.append({
                    "option_id": oid,
                    "text": opt.get("text", ""),
                    "count": count,
                    "percentage": percentage,
                })
            stat["option_statistics"] = option_statistics

        elif q_type == "text_input":
            stat["text_responses"] = [a for a in answers_list if isinstance(a, str)]

        elif q_type == "number_input":
            num_values = [a for a in answers_list if isinstance(a, (int, float))]
            if num_values:
                stat["number_statistics"] = {
                    "average": round(sum(num_values) / len(num_values), 2),
                    "min": min(num_values),
                    "max": max(num_values),
                    "values": num_values,
                }
            else:
                stat["number_statistics"] = {"average": 0, "min": 0, "max": 0, "values": []}

        version_statistics.append(stat)

    # 构建命中的问卷列表
    all_survey_ids = set()
    for sids in version_survey_ids.values():
        all_survey_ids.update(sids)
    surveys_list = []
    for sid in all_survey_ids:
        s = survey_docs.get(sid)
        if s:
            surveys_list.append({
                "survey_id": sid,
                "title": s.get("title", ""),
                "status": s.get("status", ""),
            })

    return {
        "question_ref_id": question_ref_id,
        "question_title": latest.get("title", ""),
        "question_type": latest.get("type", ""),
        "total_answers": total_answers,
        "survey_count": len(all_survey_ids),
        "surveys": surveys_list,
        "version_statistics": version_statistics,
    }
