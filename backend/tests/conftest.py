from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.main import request_validation_exception_handler
from app.middlewares import auth as auth_middleware
from app.routes import responses, statistics, surveys, questions as questions_routes
from app.services import response_service, statistics_service, survey_service, question_service


class FakeInsertResult:
    def __init__(self, inserted_id: ObjectId):
        self.inserted_id = inserted_id


class FakeDeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class FakeCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs

    def sort(self, field: str, direction: int) -> "FakeCursor":
        reverse = direction == -1
        self._docs = sorted(self._docs, key=lambda d: d.get(field), reverse=reverse)
        return self

    def skip(self, count: int) -> "FakeCursor":
        self._docs = self._docs[count:]
        return self

    def limit(self, count: int) -> "FakeCursor":
        self._docs = self._docs[:count]
        return self

    def __iter__(self):
        return iter(self._docs)


def _resolve_dot_path(doc: Any, path: str) -> Any:
    """解析点分隔路径，支持嵌套字典和数组"""
    parts = path.split(".", 1)
    key = parts[0]
    rest = parts[1] if len(parts) > 1 else None

    if isinstance(doc, dict):
        val = doc.get(key)
        if rest is None:
            return val
        if isinstance(val, list):
            # 数组中每个元素都尝试匹配
            return [_resolve_dot_path(item, rest) for item in val]
        return _resolve_dot_path(val, rest)
    return None


def _matches_value(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict) and "$elemMatch" in expected:
        if not isinstance(actual, list):
            return False
        sub_query = expected["$elemMatch"]
        return any(isinstance(item, dict) and _matches_query(item, sub_query) for item in actual)
    if isinstance(expected, dict) and "$in" in expected:
        if isinstance(actual, list):
            return any(item in expected["$in"] for item in actual)
        return actual in expected["$in"]
    if isinstance(actual, list) and not isinstance(expected, list):
        return expected in actual
    return actual == expected


def _matches_query(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
    for key, expected in query.items():
        if "." in key:
            actual = _resolve_dot_path(doc, key)
            # actual 可能是单值或列表（来自数组展开）
            if isinstance(actual, list):
                if not any(_matches_value(item, expected) for item in actual):
                    return False
            else:
                if not _matches_value(actual, expected):
                    return False
        else:
            if not _matches_value(doc.get(key), expected):
                return False
    return True


def _set_dot_path(doc: dict, path: str, value: Any) -> None:
    """设置点分隔路径的值"""
    parts = path.split(".")
    current: Any = doc
    for idx, part in enumerate(parts[:-1]):
        next_part = parts[idx + 1]

        if isinstance(current, list):
            list_idx = int(part)
            while len(current) <= list_idx:
                current.append({})
            current = current[list_idx]
            continue

        if part not in current or not isinstance(current[part], (dict, list)):
            current[part] = [] if next_part.isdigit() else {}
        current = current[part]

    last = parts[-1]
    if isinstance(current, list):
        list_idx = int(last)
        while len(current) <= list_idx:
            current.append(None)
        current[list_idx] = value
    else:
        current[last] = value


def _get_dot_path(doc: dict, path: str, default: Any = None) -> Any:
    """获取点分隔路径的值"""
    parts = path.split(".")
    current: Any = doc
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, default)
        elif isinstance(current, list) and part.isdigit():
            list_idx = int(part)
            if 0 <= list_idx < len(current):
                current = current[list_idx]
            else:
                return default
        else:
            return default
    return current


def _apply_projection(doc: Dict[str, Any], projection: Dict[str, Any]) -> Dict[str, Any]:
    """简化版 projection：支持包含式投影（field: 1）。"""
    include_fields = [field for field, flag in projection.items() if flag and field != "_id"]
    if not include_fields:
        return deepcopy(doc)

    projected: Dict[str, Any] = {"_id": doc.get("_id")}
    for field in include_fields:
        value = _get_dot_path(doc, field, None)
        if value is not None:
            _set_dot_path(projected, field, deepcopy(value))
    return projected


class FakeCollection:
    def __init__(self):
        self._docs: List[Dict[str, Any]] = []

    def insert_one(self, doc: Dict[str, Any]) -> FakeInsertResult:
        copied = dict(doc)
        copied.setdefault("_id", ObjectId())
        self._docs.append(copied)
        return FakeInsertResult(copied["_id"])

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for doc in self._docs:
            if _matches_query(doc, query):
                return doc
        return None

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None) -> FakeCursor:
        query = query or {}
        matched_docs = [doc for doc in self._docs if _matches_query(doc, query)]
        if projection is None:
            return FakeCursor(matched_docs)
        return FakeCursor([_apply_projection(doc, projection) for doc in matched_docs])

    def count_documents(self, query: Dict[str, Any]) -> int:
        return sum(1 for doc in self._docs if _matches_query(doc, query))

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> None:
        doc = self.find_one(query)
        if doc is None:
            return

        set_payload = update.get("$set", {})
        for key, value in set_payload.items():
            if "." in key:
                _set_dot_path(doc, key, value)
            else:
                doc[key] = value

        inc_payload = update.get("$inc", {})
        for key, value in inc_payload.items():
            current = _get_dot_path(doc, key, 0) if "." in key else doc.get(key, 0)
            if "." in key:
                _set_dot_path(doc, key, current + value)
            else:
                doc[key] = current + value

        push_payload = update.get("$push", {})
        for key, value in push_payload.items():
            arr = _get_dot_path(doc, key) if "." in key else doc.get(key)
            if arr is None:
                arr = []
                if "." in key:
                    _set_dot_path(doc, key, arr)
                else:
                    doc[key] = arr
            arr.append(value)

        add_to_set_payload = update.get("$addToSet", {})
        for key, value in add_to_set_payload.items():
            arr = _get_dot_path(doc, key) if "." in key else doc.get(key)
            if arr is None:
                arr = []
                if "." in key:
                    _set_dot_path(doc, key, arr)
                else:
                    doc[key] = arr
            if value not in arr:
                arr.append(value)

        pull_payload = update.get("$pull", {})
        for key, value in pull_payload.items():
            arr = _get_dot_path(doc, key) if "." in key else doc.get(key)
            if isinstance(arr, list):
                while value in arr:
                    arr.remove(value)

    def delete_many(self, query: Dict[str, Any]) -> FakeDeleteResult:
        before = len(self._docs)
        self._docs = [doc for doc in self._docs if not _matches_query(doc, query)]
        return FakeDeleteResult(before - len(self._docs))

    def delete_one(self, query: Dict[str, Any]) -> FakeDeleteResult:
        for idx, doc in enumerate(self._docs):
            if _matches_query(doc, query):
                del self._docs[idx]
                return FakeDeleteResult(1)
        return FakeDeleteResult(0)


class FakeDB:
    def __init__(self):
        self.users = FakeCollection()
        self.surveys = FakeCollection()
        self.responses = FakeCollection()
        self.questions = FakeCollection()


@dataclass
class AuthContext:
    user_id: str
    username: str


@dataclass
class TestContext:
    db: FakeDB
    auth: AuthContext

    def switch_user(self, user_id: str, username: str) -> None:
        self.auth.user_id = user_id
        self.auth.username = username

    def create_user(self, username: str) -> str:
        user_id = ObjectId()
        self.db.users.insert_one(
            {
                "_id": user_id,
                "username": username,
                "password_hash": "hash",
                "created_at": datetime.now(),
            }
        )
        return str(user_id)


def _create_question_doc(db: FakeDB, user_id: str, q: Dict[str, Any]) -> str:
    """在 FakeDB 的 questions 集合中创建题目文档，返回 question_ref_id（字符串）"""
    now = datetime.now()
    version_obj = {
        "version_number": 1,
        "created_at": now,
        "updated_by": user_id,
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
            "creator": user_id,
            "shared_with": [],
            "banked_by": [],
        },
        "versions": [version_obj],
    }
    result = db.questions.insert_one(question_doc)
    return str(result.inserted_id)


def convert_to_refs(db: FakeDB, user_id: str, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将旧格式的内嵌题目列表转换为第二阶段引用格式。
    自动在 FakeDB 中创建对应的 question 文档。
    """
    refs = []
    for q in questions:
        ref_id = _create_question_doc(db, user_id, q)
        ref_item = {
            "question_id": q["question_id"],
            "order": q.get("order", 0),
            "question_ref_id": ref_id,
            "version_number": 1,
        }
        if q.get("logic"):
            ref_item["logic"] = q["logic"]
        refs.append(ref_item)
    return refs


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch):
    db = FakeDB()

    creator_id = ObjectId()
    db.users.insert_one(
        {
            "_id": creator_id,
            "username": "creator",
            "password_hash": "hash",
            "created_at": datetime.now(),
        }
    )

    auth = AuthContext(user_id=str(creator_id), username="creator")
    ctx = TestContext(db=db, auth=auth)

    monkeypatch.setattr(survey_service, "get_db", lambda: db)
    monkeypatch.setattr(response_service, "get_db", lambda: db)
    monkeypatch.setattr(statistics_service, "get_db", lambda: db)
    monkeypatch.setattr(question_service, "get_db", lambda: db)

    app = FastAPI()
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.include_router(surveys.router, prefix="/surveys")
    app.include_router(questions_routes.router, prefix="/questions")
    app.include_router(responses.router)
    app.include_router(statistics.router)

    app.dependency_overrides[auth_middleware.get_current_user] = lambda: {
        "user_id": auth.user_id,
        "username": auth.username,
    }
    app.dependency_overrides[auth_middleware.get_optional_user] = lambda: {
        "user_id": auth.user_id,
        "username": auth.username,
    }

    client = TestClient(app)
    return client, ctx


def create_base_questions_raw() -> List[Dict[str, Any]]:
    """返回旧格式的内嵌题目（用于 convert_to_refs）"""
    return [
        {
            "question_id": "q1",
            "type": "single_choice",
            "title": "是否已有开发经验",
            "required": True,
            "order": 1,
            "options": [
                {"option_id": "opt_yes", "text": "有"},
                {"option_id": "opt_no", "text": "没有"},
            ],
            "logic": {
                "enabled": True,
                "rules": [
                    {
                        "condition": {"type": "select_option", "option_id": "opt_yes"},
                        "action": {"type": "jump_to", "target_question_id": "q3"},
                    }
                ],
            },
        },
        {
            "question_id": "q2",
            "type": "text_input",
            "title": "请描述你的困难",
            "required": True,
            "order": 2,
            "validation": {"min_length": 2, "max_length": 50},
        },
        {
            "question_id": "q3",
            "type": "number_input",
            "title": "你学习 Python 的年限",
            "required": True,
            "order": 3,
            "validation": {"min_value": 0, "max_value": 30, "integer_only": True},
        },
    ]


def create_base_questions(db: FakeDB = None, user_id: str = None) -> List[Dict[str, Any]]:
    """返回引用格式的题目列表（需传入 db 和 user_id）"""
    raw = create_base_questions_raw()
    if db is not None and user_id is not None:
        return convert_to_refs(db, user_id, raw)
    return raw


def create_multi_type_questions_raw() -> List[Dict[str, Any]]:
    """返回旧格式的多类型题目"""
    return [
        {
            "question_id": "q_single",
            "type": "single_choice",
            "title": "最常用语言",
            "required": True,
            "order": 1,
            "options": [
                {"option_id": "opt_py", "text": "Python"},
                {"option_id": "opt_js", "text": "JavaScript"},
            ],
        },
        {
            "question_id": "q_multi",
            "type": "multiple_choice",
            "title": "常用工具",
            "required": True,
            "order": 2,
            "options": [
                {"option_id": "opt_git", "text": "Git"},
                {"option_id": "opt_docker", "text": "Docker"},
                {"option_id": "opt_ci", "text": "CI"},
            ],
            "validation": {"min_selected": 1, "max_selected": 3},
        },
        {
            "question_id": "q_text",
            "type": "text_input",
            "title": "一句话建议",
            "required": False,
            "order": 3,
            "validation": {"max_length": 100},
        },
        {
            "question_id": "q_num",
            "type": "number_input",
            "title": "每天编码小时数",
            "required": True,
            "order": 4,
            "validation": {"min_value": 0, "max_value": 24, "integer_only": False},
        },
    ]


def create_multi_type_questions(db: FakeDB = None, user_id: str = None) -> List[Dict[str, Any]]:
    """返回引用格式的多类型题目列表"""
    raw = create_multi_type_questions_raw()
    if db is not None and user_id is not None:
        return convert_to_refs(db, user_id, raw)
    return raw
