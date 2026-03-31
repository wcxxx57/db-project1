"""JWT 认证中间件"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from passlib.context import CryptContext
from app.config import settings

# 密码哈希工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token 提取器
security = HTTPBearer()

# 可选的 Bearer token 提取器（用于允许匿名访问的接口）
optional_security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """对密码进行哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, username: str) -> str:
    """创建 JWT token"""
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "username": username,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_token(token: str) -> dict:
    """解析 JWT token，返回 payload"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的 Token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """从请求中提取并验证当前用户（必须登录）

    用法：在路由函数参数中添加 current_user: dict = Depends(get_current_user)
    返回：{"user_id": "...", "username": "..."}
    """
    payload = decode_token(credentials.credentials)
    return {
        "user_id": payload["sub"],
        "username": payload["username"],
    }


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[dict]:
    """从请求中提取当前用户（可选，用于允许匿名访问的接口）

    用法：在路由函数参数中添加 current_user: Optional[dict] = Depends(get_optional_user)
    返回：{"user_id": "...", "username": "..."} 或 None（未登录）
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return {
            "user_id": payload["sub"],
            "username": payload["username"],
        }
    except HTTPException:
        return None
