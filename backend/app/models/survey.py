"""问卷 & 题目数据模型"""

from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field


# ============ 跳转逻辑相关模型 ============

class SelectOptionCondition(BaseModel):
    """单选匹配条件"""
    type: str = Field(default="select_option", description="条件类型")
    option_id: str = Field(..., description="当选择了该选项时触发")


class ContainsOptionCondition(BaseModel):
    """多选包含条件"""
    type: str = Field(default="contains_option", description="条件类型")
    option_ids: List[str] = Field(..., description="当选择的选项中包含这些时触发")


class NumberCompareCondition(BaseModel):
    """数字比较条件"""
    type: str = Field(default="number_compare", description="条件类型")
    operator: str = Field(..., description="操作符: eq/ne/gt/gte/lt/lte/between")
    value: Optional[float] = Field(None, description="比较值（用于 eq/ne/gt/gte/lt/lte）")
    min_value: Optional[float] = Field(None, description="区间最小值（用于 between）")
    max_value: Optional[float] = Field(None, description="区间最大值（用于 between）")


class LogicAction(BaseModel):
    """跳转动作"""
    type: str = Field(..., description="动作类型: jump_to / end_survey")
    target_question_id: Optional[str] = Field(None, description="跳转目标题目 ID（仅 jump_to 使用）")


class LogicRule(BaseModel):
    """跳转规则"""
    condition: dict = Field(..., description="条件（SelectOptionCondition / ContainsOptionCondition / NumberCompareCondition）")
    action: LogicAction = Field(..., description="动作")


class QuestionLogic(BaseModel):
    """题目跳转逻辑"""
    enabled: bool = Field(default=False, description="是否启用跳转逻辑")
    rules: List[LogicRule] = Field(default_factory=list, description="跳转规则列表")


# ============ 校验规则模型 ============

class QuestionValidation(BaseModel):
    """题目校验规则"""
    # 多选题校验
    min_selected: Optional[int] = Field(None, description="最少选择数量（仅 multiple_choice）")
    max_selected: Optional[int] = Field(None, description="最多选择数量（仅 multiple_choice）")
    exact_selected: Optional[int] = Field(None, description="必须选择的精确数量（仅 multiple_choice）")

    # 文本填空校验
    min_length: Optional[int] = Field(None, description="最少字数（仅 text_input）")
    max_length: Optional[int] = Field(None, description="最多字数（仅 text_input）")

    # 数字填空校验
    min_value: Optional[float] = Field(None, description="最小值（仅 number_input）")
    max_value: Optional[float] = Field(None, description="最大值（仅 number_input）")
    integer_only: Optional[bool] = Field(None, description="是否必须为整数（仅 number_input）")


# ============ 选项模型 ============

class QuestionOption(BaseModel):
    """题目选项"""
    option_id: str = Field(..., description="选项标识，如 opt1, opt2")
    text: str = Field(..., description="选项文本")


# ============ 题目模型 ============

class Question(BaseModel):
    """题目"""
    question_id: str = Field(..., description="题目唯一标识，如 q1, q2")
    type: str = Field(..., description="题目类型: single_choice / multiple_choice / text_input / number_input")
    title: str = Field(..., description="题目文本")
    required: bool = Field(default=True, description="是否必答")
    order: int = Field(..., description="显示顺序")
    options: Optional[List[QuestionOption]] = Field(None, description="选项列表（仅选择题使用）")
    validation: Optional[QuestionValidation] = Field(None, description="校验规则")
    logic: Optional[QuestionLogic] = Field(None, description="跳转逻辑")


# ============ 问卷设置模型 ============

class SurveySettings(BaseModel):
    """问卷设置"""
    allow_anonymous: bool = Field(default=True, description="是否允许匿名填写")
    allow_multiple: bool = Field(default=False, description="是否允许同一用户多次提交")


# ============ 请求模型 ============

class SurveyCreateRequest(BaseModel):
    """创建问卷请求"""
    title: str = Field(..., min_length=1, max_length=200, description="问卷标题")
    description: Optional[str] = Field(None, max_length=2000, description="问卷说明")
    settings: Optional[SurveySettings] = Field(default_factory=SurveySettings, description="问卷设置")
    deadline: Optional[datetime] = Field(None, description="截止时间")


class SurveyUpdateRequest(BaseModel):
    """更新问卷请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="问卷标题")
    description: Optional[str] = Field(None, max_length=2000, description="问卷说明")
    settings: Optional[SurveySettings] = Field(None, description="问卷设置")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    questions: Optional[List[Question]] = Field(None, description="题目列表")


# ============ 响应模型 ============

class SurveyResponse(BaseModel):
    """问卷响应"""
    id: str = Field(..., description="问卷 ID")
    title: str = Field(..., description="问卷标题")
    description: Optional[str] = Field(None, description="问卷说明")
    creator_id: str = Field(..., description="创建者 ID")
    access_code: str = Field(..., description="访问码")
    status: str = Field(..., description="状态: draft / published / closed")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    response_count: int = Field(default=0, description="已收集答卷数")
    settings: SurveySettings = Field(..., description="问卷设置")
    questions: List[Question] = Field(default_factory=list, description="题目列表")


class SurveyListItem(BaseModel):
    """问卷列表项（不含题目详情）"""
    id: str = Field(..., description="问卷 ID")
    title: str = Field(..., description="问卷标题")
    description: Optional[str] = Field(None, description="问卷说明")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    response_count: int = Field(default=0, description="已收集答卷数")
    access_code: str = Field(..., description="访问码")


# ============ 数据库文档模型 ============

class SurveyInDB(BaseModel):
    """数据库中的问卷文档结构"""
    title: str
    description: Optional[str] = None
    creator_id: str
    access_code: str
    status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    response_count: int = 0
    settings: dict = Field(default_factory=lambda: {"allow_anonymous": True, "allow_multiple": False})
    questions: list = Field(default_factory=list)
