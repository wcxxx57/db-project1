from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError

from app.routes.auth import router as auth_router
from app.main import request_validation_exception_handler
from app.services import auth_service
from app.middlewares.auth import hash_password as real_hash_password, verify_password as real_verify_password


class FakeInsertResult:
	def __init__(self, inserted_id: str):
		self.inserted_id = inserted_id


class FakeUsersCollection:
	def __init__(self):
		self._docs = []
		self._id_counter = 1

	def find_one(self, query):
		for doc in self._docs:
			matched = True
			for key, value in query.items():
				if doc.get(key) != value:
					matched = False
					break
			if matched:
				return doc
		return None

	def insert_one(self, user_doc):
		inserted = dict(user_doc)
		inserted["_id"] = str(self._id_counter)
		self._id_counter += 1
		self._docs.append(inserted)
		return FakeInsertResult(inserted["_id"])


class FakeDB:
	def __init__(self):
		self.users = FakeUsersCollection()


def build_test_client():
	fake_db = FakeDB()

	app = FastAPI()
	app.add_exception_handler(
		RequestValidationError,
		request_validation_exception_handler,
	)
	app.include_router(auth_router, prefix="/auth")

	auth_service.get_db = lambda: fake_db
	auth_service.hash_password = lambda password: f"hashed::{password}"
	auth_service.verify_password = (
		lambda plain_password, hashed_password: hashed_password == f"hashed::{plain_password}"
	)
	auth_service.create_access_token = (
		lambda user_id, username: f"token-{user_id}-{username}"
	)

	return TestClient(app)


def build_test_client_with_real_password_hash():
	fake_db = FakeDB()

	app = FastAPI()
	app.add_exception_handler(
		RequestValidationError,
		request_validation_exception_handler,
	)
	app.include_router(auth_router, prefix="/auth")

	auth_service.get_db = lambda: fake_db
	auth_service.hash_password = real_hash_password
	auth_service.verify_password = real_verify_password
	auth_service.create_access_token = (
		lambda user_id, username: f"token-{user_id}-{username}"
	)

	return TestClient(app)


def test_register_success_response_shape():
	client = build_test_client()

	response = client.post(
		"/auth/register",
		json={
			"username": "wcx_user",
			"password": "Password123",
		},
	)

	assert response.status_code == 200
	payload = response.json()
	assert payload["code"] == 0
	assert payload["message"] == "success"
	assert payload["data"]["username"] == "wcx_user"
	assert "email" not in payload["data"]
	datetime.fromisoformat(payload["data"]["created_at"].replace("Z", "+00:00"))


def test_register_duplicate_username_returns_1001():
	client = build_test_client()

	first_payload = {
		"username": "same_name",
		"password": "Password123",
	}
	second_payload = {
		"username": "same_name",
		"password": "Password123",
	}

	first_response = client.post("/auth/register", json=first_payload)
	second_response = client.post("/auth/register", json=second_payload)

	assert first_response.status_code == 200
	assert second_response.status_code == 400
	assert second_response.json()["code"] == 1001


def test_register_prefix_usernames_should_both_succeed():
	client = build_test_client()

	first_response = client.post(
		"/auth/register",
		json={
			"username": "ddd",
			"password": "Password123",
		},
	)
	second_response = client.post(
		"/auth/register",
		json={
			"username": "ddd1",
			"password": "Password123",
		},
	)

	assert first_response.status_code == 200
	assert second_response.status_code == 200
	assert first_response.json()["code"] == 0
	assert second_response.json()["code"] == 0


def test_login_success_returns_token_and_user():
	client = build_test_client()

	register_payload = {
		"username": "login_user",
		"password": "Password123",
	}
	login_payload = {
		"username": "login_user",
		"password": "Password123",
	}

	register_response = client.post("/auth/register", json=register_payload)
	login_response = client.post("/auth/login", json=login_payload)

	assert register_response.status_code == 200
	assert login_response.status_code == 200
	payload = login_response.json()
	assert payload["code"] == 0
	assert payload["data"]["token_type"] == "bearer"
	assert payload["data"]["access_token"]
	assert payload["data"]["user"]["username"] == "login_user"


def test_login_wrong_password_returns_1002():
	client = build_test_client()

	client.post(
		"/auth/register",
		json={
			"username": "wrong_pwd_user",
			"password": "Password123",
		},
	)

	response = client.post(
		"/auth/login",
		json={
			"username": "wrong_pwd_user",
			"password": "wrong-password",
		},
	)

	assert response.status_code == 400
	assert response.json()["code"] == 1002


def test_login_nonexistent_user_returns_1004():
	client = build_test_client()

	response = client.post(
		"/auth/login",
		json={
			"username": "missing_user",
			"password": "Password123",
		},
	)

	assert response.status_code == 400
	payload = response.json()
	assert payload["code"] == 1004
	assert payload["message"] == "未发现该用户，请先注册"


def test_register_and_login_long_password_with_real_hash_success():
	client = build_test_client_with_real_password_hash()

	long_password = "A" * 100
	register_response = client.post(
		"/auth/register",
		json={
			"username": "long_pwd_user",
			"password": long_password,
		},
	)

	assert register_response.status_code == 200
	assert register_response.json()["code"] == 0

	login_response = client.post(
		"/auth/login",
		json={
			"username": "long_pwd_user",
			"password": long_password,
		},
	)

	assert login_response.status_code == 200
	payload = login_response.json()
	assert payload["code"] == 0
	assert payload["data"]["token_type"] == "bearer"
	assert payload["data"]["user"]["username"] == "long_pwd_user"


def test_register_password_too_short_returns_400_with_precise_message():
	client = build_test_client()

	response = client.post(
		"/auth/register",
		json={
			"username": "short_pwd_user",
			"password": "1234567",
		},
	)

	assert response.status_code == 400
	payload = response.json()
	assert payload["code"] == 3001
	assert payload["message"] == "密码不足8位，请至少输入8位"


def test_register_password_min_length_8_success():
	client = build_test_client()

	response = client.post(
		"/auth/register",
		json={
			"username": "min8_pwd_user",
			"password": "12345678",
		},
	)

	assert response.status_code == 200
	assert response.json()["code"] == 0


def test_register_password_too_long_returns_400_with_precise_message():
	client = build_test_client()

	response = client.post(
		"/auth/register",
		json={
			"username": "too_long_pwd_user",
			"password": "a" * 129,
		},
	)

	assert response.status_code == 400
	payload = response.json()
	assert payload["code"] == 3001
	assert payload["message"] == "密码超过128位，请输入不超过128位"


def test_register_username_too_short_returns_400_with_precise_message():
	client = build_test_client()

	response = client.post(
		"/auth/register",
		json={
			"username": "a",
			"password": "Password123",
		},
	)

	assert response.status_code == 400
	payload = response.json()
	assert payload["code"] == 3001
	assert payload["message"] == "用户名不足2位，请至少输入2位"


def test_register_username_min_length_2_success():
	client = build_test_client()

	response = client.post(
		"/auth/register",
		json={
			"username": "ab",
			"password": "Password123",
		},
	)

	assert response.status_code == 200
	assert response.json()["code"] == 0


def test_register_username_max_length_50_success():
	client = build_test_client()

	response = client.post(
		"/auth/register",
		json={
			"username": "a" * 50,
			"password": "Password123",
		},
	)

	assert response.status_code == 200
	assert response.json()["code"] == 0


def test_register_username_too_long_returns_400_with_precise_message():
	client = build_test_client()

	response = client.post(
		"/auth/register",
		json={
			"username": "a" * 51,
			"password": "Password123",
		},
	)

	assert response.status_code == 400
	payload = response.json()
	assert payload["code"] == 3001
	assert payload["message"] == "用户名超过50位，请输入不超过50位"
