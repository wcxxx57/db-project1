"""用户认证业务逻辑"""

from datetime import datetime, timezone
from typing import Dict, Any

from pymongo.errors import DuplicateKeyError

from app.database import get_db
from app.middlewares.auth import hash_password, verify_password, create_access_token


class AuthServiceError(Exception):
	"""认证业务异常，携带业务码与 HTTP 状态码。"""

	def __init__(self, business_code: int, message: str, http_status: int):
		super().__init__(message)
		self.business_code = business_code
		self.message = message
		self.http_status = http_status


def _serialize_user(user_doc: Dict[str, Any]) -> Dict[str, Any]:
	return {
		"user_id": str(user_doc["_id"]),
		"username": user_doc["username"],
		"created_at": user_doc["created_at"],
	}


def register_user(username: str, password: str) -> Dict[str, Any]:
	"""注册用户。"""
	db = get_db()

	existing_by_username = db.users.find_one({"username": username})
	if existing_by_username is not None:
		raise AuthServiceError(1001, "用户名已存在", 400)

	now = datetime.now()
	user_doc = {
		"username": username,
		"password_hash": hash_password(password),
		"created_at": now,
	}

	try:
		insert_result = db.users.insert_one(user_doc)
	except DuplicateKeyError:
		raise AuthServiceError(1001, "用户名已存在", 400) from None

	user_doc["_id"] = insert_result.inserted_id
	return _serialize_user(user_doc)


def login_user(username: str, password: str) -> Dict[str, Any]:
	"""用户登录并返回 token。"""
	db = get_db()
	user_doc = db.users.find_one({"username": username})
	if user_doc is None:
		raise AuthServiceError(1004, "未发现该用户，请先注册", 400)

	if not verify_password(password, user_doc["password_hash"]):
		raise AuthServiceError(1002, "用户名或密码错误", 400)

	user = _serialize_user(user_doc)
	token = create_access_token(user_id=user["user_id"], username=user["username"])
	return {
		"access_token": token,
		"token_type": "bearer",
		"user": user,
	}
