from __future__ import annotations

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
from app.routes import responses, statistics, surveys
from app.services import response_service, statistics_service, survey_service


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


def _matches_value(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict) and "$in" in expected:
        return actual in expected["$in"]
    return actual == expected


def _matches_query(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
    for key, expected in query.items():
        if not _matches_value(doc.get(key), expected):
            return False
    return True


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

    def find(self, query: Optional[Dict[str, Any]] = None) -> FakeCursor:
        query = query or {}
        return FakeCursor([doc for doc in self._docs if _matches_query(doc, query)])

    def count_documents(self, query: Dict[str, Any]) -> int:
        return sum(1 for doc in self._docs if _matches_query(doc, query))

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> None:
        doc = self.find_one(query)
        if doc is None:
            return

        set_payload = update.get("$set", {})
        for key, value in set_payload.items():
            doc[key] = value

        inc_payload = update.get("$inc", {})
        for key, value in inc_payload.items():
            doc[key] = doc.get(key, 0) + value

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
                "created_at": datetime.now(timezone.utc),
            }
        )
        return str(user_id)


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch):
    db = FakeDB()

    creator_id = ObjectId()
    db.users.insert_one(
        {
            "_id": creator_id,
            "username": "creator",
            "password_hash": "hash",
            "created_at": datetime.now(timezone.utc),
        }
    )

    auth = AuthContext(user_id=str(creator_id), username="creator")
    ctx = TestContext(db=db, auth=auth)

    monkeypatch.setattr(survey_service, "get_db", lambda: db)
    monkeypatch.setattr(response_service, "get_db", lambda: db)
    monkeypatch.setattr(statistics_service, "get_db", lambda: db)

    app = FastAPI()
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.include_router(surveys.router, prefix="/surveys")
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


def create_base_questions() -> List[Dict[str, Any]]:
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


def create_multi_type_questions() -> List[Dict[str, Any]]:
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
