"""用户数据模型"""

from datetime import datetime
from pydantic import BaseModel, Field


# ============ 请求模型 ============

class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=8, max_length=128, description="密码")


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


# ============ 响应模型 ============

class UserResponse(BaseModel):
    """用户信息响应（不含密码）"""
    user_id: str = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    created_at: datetime = Field(..., description="注册时间")


class TokenResponse(BaseModel):
    """登录成功返回的 token"""
    access_token: str = Field(..., description="JWT token")
    token_type: str = Field(default="bearer", description="token 类型")
    user: UserResponse = Field(..., description="用户信息")


# ============ 数据库文档模型 ============

class UserInDB(BaseModel):
    """数据库中的用户文档结构"""
    username: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
