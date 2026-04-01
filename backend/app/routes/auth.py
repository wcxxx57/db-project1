"""认证路由"""

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.models.user import UserRegisterRequest, UserLoginRequest
from app.services.auth_service import register_user, login_user, AuthServiceError
from app.utils.response import success_response, error_response


router = APIRouter()


@router.post("/register")
def register(payload: UserRegisterRequest):
	try:
		user_data = register_user(
			username=payload.username,
			password=payload.password,
		)
		return JSONResponse(
			status_code=200,
			content=jsonable_encoder(success_response(data=user_data)),
		)
	except AuthServiceError as exc:
		return JSONResponse(
			status_code=exc.http_status,
			content=error_response(code=exc.business_code, message=exc.message),
		)


@router.post("/login")
def login(payload: UserLoginRequest):
	try:
		login_data = login_user(username=payload.username, password=payload.password)
		return JSONResponse(
			status_code=200,
			content=jsonable_encoder(success_response(data=login_data)),
		)
	except AuthServiceError as exc:
		return JSONResponse(
			status_code=exc.http_status,
			content=error_response(code=exc.business_code, message=exc.message),
		)
