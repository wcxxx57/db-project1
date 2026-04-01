"""答卷数据模型"""

from datetime import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field


# ============ 答案模型 ============

class Answer(BaseModel):
    """单个题目的答案"""
    question_id: str = Field(..., description="对应的题目 ID")
    answer: Union[str, List[str], int, float] = Field(
        ...,
        description="答案值: single_choice→str, multiple_choice→[str], text_input→str, number_input→Number"
    )


# ============ 请求模型 ============

class ResponseSubmitRequest(BaseModel):
    """提交答卷请求"""
    survey_id: str = Field(..., description="问卷 ID")
    access_code: str = Field(..., description="问卷访问码")
    answers: List[Answer] = Field(..., description="答案列表")
    completion_time: Optional[int] = Field(None, description="完成问卷所用秒数")


# ============ 响应模型 ============

class ResponseDetail(BaseModel):
    """答卷详情响应"""
    response_id: str = Field(..., description="答卷 ID")
    survey_id: str = Field(..., description="问卷 ID")
    respondent_id: Optional[str] = Field(None, description="答题者 ID（匿名时为 null）")
    is_anonymous: bool = Field(..., description="是否为匿名提交")
    submitted_at: datetime = Field(..., description="提交时间")
    answers: List[Answer] = Field(..., description="答案列表")
    completion_time: Optional[int] = Field(None, description="完成用时（秒）")


class ResponseListItem(BaseModel):
    """答卷列表项"""
    response_id: str = Field(..., description="答卷 ID")
    respondent_id: Optional[str] = Field(None, description="答题者 ID")
    is_anonymous: bool = Field(..., description="是否匿名")
    submitted_at: datetime = Field(..., description="提交时间")
    completion_time: Optional[int] = Field(None, description="完成用时（秒）")


# ============ 统计模型 ============

class OptionStatistic(BaseModel):
    """选项统计"""
    option_id: str = Field(..., description="选项 ID")
    text: str = Field(..., description="选项文本")
    count: int = Field(..., description="选择次数")
    percentage: float = Field(..., description="百分比")


class QuestionStatistic(BaseModel):
    """单个题目的统计结果"""
    question_id: str = Field(..., description="题目 ID")
    title: str = Field(..., description="题目文本")
    type: str = Field(..., description="题目类型")
    total_answers: int = Field(..., description="回答总数")

    # 选择题统计
    option_statistics: Optional[List[OptionStatistic]] = Field(None, description="选项统计（选择题）")

    # 填空题统计
    text_answers: Optional[List[str]] = Field(None, description="所有文本答案（文本填空）")

    # 数字填空统计
    number_answers: Optional[List[float]] = Field(None, description="所有数字答案（数字填空）")
    average: Optional[float] = Field(None, description="平均值（数字填空）")
    min_val: Optional[float] = Field(None, description="最小值（数字填空）")
    max_val: Optional[float] = Field(None, description="最大值（数字填空）")


class SurveyStatistics(BaseModel):
    """问卷整体统计结果"""
    survey_id: str = Field(..., description="问卷 ID")
    survey_title: str = Field(..., description="问卷标题")
    total_responses: int = Field(..., description="总答卷数")
    question_statistics: List[QuestionStatistic] = Field(..., description="各题目统计")


# ============ 数据库文档模型 ============

class ResponseInDB(BaseModel):
    """数据库中的答卷文档结构"""
    survey_id: str
    respondent_id: Optional[str] = None
    is_anonymous: bool = True
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    answers: list = Field(default_factory=list)
    completion_time: Optional[int] = None
