"""一次性数据迁移脚本：将第一阶段数据迁移到第二阶段结构

迁移范围：
1. 从现有 surveys.questions 抽取题目，写入 questions 集合并建立版本 v1
2. 回填 surveys.questions[*].question_ref_id、version_number
3. 对已有 responses.answers 回填 question_ref_id、version_number

使用方法：
    cd backend
    python -m scripts.migrate_phase2
"""

import sys
import os

# 确保可以 import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from bson import ObjectId

from app.database import get_db


def migrate():
    db = get_db()

    print("=" * 60)
    print("第二阶段数据迁移开始")
    print("=" * 60)

    # 统计
    surveys_migrated = 0
    questions_created = 0
    responses_migrated = 0

    # 遍历所有问卷
    all_surveys = list(db.surveys.find({}))
    print(f"共发现 {len(all_surveys)} 个问卷需要处理")

    for survey in all_surveys:
        survey_id = survey["_id"]
        creator_id = str(survey.get("creator_id", ""))
        questions = survey.get("questions", [])

        if not questions:
            continue

        # 检查是否已经迁移过（检查第一个题目是否已有 question_ref_id）
        first_q = questions[0]
        if first_q.get("question_ref_id"):
            print(f"  问卷 {survey_id} 已经迁移过，跳过")
            continue

        # 为该问卷的每个内嵌题目创建独立题目文档
        # 建立 question_id -> question_ref_id 的映射
        qid_to_ref = {}

        for q in questions:
            qid = q.get("question_id")
            now = datetime.now()

            version_obj = {
                "version_number": 1,
                "created_at": now,
                "updated_by": creator_id,
                "parent_version_number": None,
                "type": q.get("type", ""),
                "title": q.get("title", ""),
                "required": q.get("required", True),
                "options": q.get("options"),
                "validation": q.get("validation"),
            }

            question_doc = {
                "latest_version_number": 1,
                "access_control": {
                    "creator": creator_id,
                    "shared_with": [],
                    "banked_by": [],
                },
                "versions": [version_obj],
            }

            result = db.questions.insert_one(question_doc)
            ref_id = str(result.inserted_id)
            qid_to_ref[qid] = ref_id
            questions_created += 1

        # 更新问卷的 questions 数组为引用格式
        new_questions = []
        for q in questions:
            qid = q.get("question_id")
            ref_id = qid_to_ref.get(qid)
            new_q = {
                "question_id": qid,
                "order": q.get("order", 0),
                "logic": q.get("logic"),
                "question_ref_id": ref_id,
                "version_number": 1,
            }
            new_questions.append(new_q)

        db.surveys.update_one(
            {"_id": survey_id},
            {"$set": {"questions": new_questions}},
        )
        surveys_migrated += 1

        # 更新该问卷的所有答卷
        responses = list(db.responses.find({"survey_id": survey_id}))
        for resp in responses:
            answers = resp.get("answers", [])
            updated_answers = []
            for ans in answers:
                ans_qid = ans.get("question_id")
                ref_id = qid_to_ref.get(ans_qid)
                updated_ans = dict(ans)
                updated_ans["question_ref_id"] = ref_id
                updated_ans["version_number"] = 1
                updated_answers.append(updated_ans)

            db.responses.update_one(
                {"_id": resp["_id"]},
                {"$set": {"answers": updated_answers}},
            )
            responses_migrated += 1

        print(f"  问卷 {survey_id}: {len(questions)} 题已迁移, {len(responses)} 份答卷已更新")

    print("=" * 60)
    print(f"迁移完成！")
    print(f"  问卷迁移: {surveys_migrated}")
    print(f"  题目创建: {questions_created}")
    print(f"  答卷更新: {responses_migrated}")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
