"""MongoDB 数据库连接模块"""

from datetime import timezone

from pymongo import MongoClient
from pymongo.database import Database
from app.config import settings

# 全局数据库客户端和实例
_client: MongoClient | None = None
_db: Database | None = None


def get_db() -> Database:
    """获取数据库实例（单例模式）"""
    global _client, _db
    if _db is None:
        _client = MongoClient(settings.MONGODB_URI, tz_aware=True, tzinfo=timezone.utc)
        _db = _client[settings.MONGODB_DB_NAME]
    return _db


def close_db():
    """关闭数据库连接"""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None


def init_indexes():
    """初始化数据库索引（应用启动时调用）"""
    db = get_db()

    # users 集合索引
    db.users.create_index("username", unique=True)

    # surveys 集合索引
    db.surveys.create_index("creator_id")
    db.surveys.create_index("access_code", unique=True)
    db.surveys.create_index("status")
    db.surveys.create_index([("created_at", -1)])
    # 第二阶段新增：反查"哪些问卷使用了这道题"
    db.surveys.create_index("questions.question_ref_id")

    # responses 集合索引
    db.responses.create_index([("survey_id", 1), ("submitted_at", -1)])
    db.responses.create_index([("survey_id", 1), ("respondent_id", 1)])
    db.responses.create_index("respondent_id")
    # 第二阶段新增：跨问卷统计
    db.responses.create_index("answers.question_ref_id")

    # 第二阶段新增：questions 集合索引
    db.questions.create_index("access_control.creator")
    db.questions.create_index("access_control.shared_with")
    db.questions.create_index("access_control.banked_by")
