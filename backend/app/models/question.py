"""独立题目数据模型（第二阶段新增）"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============ 题目版本内容模型 ============

class QuestionVersionContent(BaseModel):
    """题目版本的具体内容"""
    type: str = Field(..., description="题目类型: single_choice / multiple_choice / text_input / number_input")
    title: str = Field(..., description="题目文本")
    options: Optional[List[dict]] = Field(None, description="选项列表 [{option_id, text}]")
    validation: Optional[dict] = Field(None, description="校验规则")


# ============ 请求模型 ============

class QuestionCreateRequest(BaseModel):
    """创建题目请求"""
    type: str = Field(..., description="题目类型")
    title: str = Field(..., min_length=1, max_length=500, description="题目文本")
    options: Optional[List[dict]] = Field(None, description="选项列表")
    validation: Optional[dict] = Field(None, description="校验规则")


class QuestionNewVersionRequest(BaseModel):
    """创建题目新版本请求"""
    type: str = Field(..., description="题目类型")
    title: str = Field(..., min_length=1, max_length=500, description="题目文本")
    options: Optional[List[dict]] = Field(None, description="选项列表")
    validation: Optional[dict] = Field(None, description="校验规则")
    parent_version_number: Optional[int] = Field(None, description="基于哪个版本创建（可选）")


class QuestionUpdateVersionRequest(BaseModel):
    """更新指定版本内容请求（原地修改，仅当该版本未被已发布/已关闭问卷使用时允许）"""
    type: str = Field(..., description="题目类型")
    title: str = Field(..., min_length=1, max_length=500, description="题目文本")
    options: Optional[List[dict]] = Field(None, description="选项列表")
    validation: Optional[dict] = Field(None, description="校验规则")


class QuestionShareRequest(BaseModel):
    """共享题目请求"""
    username: str = Field(..., min_length=1, description="共享目标用户名")


class QuestionUnshareRequest(BaseModel):
    """取消共享请求"""
    username: str = Field(..., min_length=1, description="取消共享的用户名")


# ============ 响应模型 ============

class QuestionVersionResponse(BaseModel):
    """题目版本响应"""
    version_number: int
    created_at: datetime
    updated_by: str
    parent_version_number: Optional[int] = None
    type: str
    title: str
    options: Optional[List[dict]] = None
    validation: Optional[dict] = None


class QuestionDetailResponse(BaseModel):
    """题目详情响应"""
    question_id: str = Field(..., description="题目谱系 ID")
    latest_version_number: int
    creator: str
    shared_with: List[str] = Field(default_factory=list)
    banked_by: List[str] = Field(default_factory=list)
    versions: List[QuestionVersionResponse] = Field(default_factory=list)


class QuestionListItem(BaseModel):
    """题目列表项"""
    question_id: str
    latest_version_number: int
    creator: str
    latest_title: str = Field(..., description="最新版本的题目文本")
    latest_type: str = Field(..., description="最新版本的题目类型")
    created_at: datetime


class QuestionUsageItem(BaseModel):
    """题目使用情况"""
    survey_id: str
    survey_title: str
    survey_status: str
    version_number: int
