/* ==============================
   统一类型定义（第二阶段扩展）
   ============================== */

// ---- API 通用 ----
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// ---- 用户 ----
export interface UserInfo {
  user_id: string;
  username: string;
  created_at: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: UserInfo;
}

// ---- 问卷设置 ----
export interface SurveySettings {
  allow_anonymous: boolean;
  allow_multiple: boolean;
}

// ---- 选项 ----
export interface QuestionOption {
  option_id: string;
  text: string;
}

// ---- 校验规则 ----
export interface QuestionValidation {
  min_selected?: number;
  max_selected?: number;
  exact_selected?: number;
  min_length?: number;
  max_length?: number;
  min_value?: number;
  max_value?: number;
  integer_only?: boolean;
}

// ---- 跳转逻辑 ----
export interface LogicCondition {
  type: "select_option" | "contains_option" | "number_compare";
  option_id?: string;
  option_ids?: string[];
  match_type?: "any" | "all";
  operator?: "eq" | "ne" | "gt" | "gte" | "lt" | "lte" | "between";
  value?: number;
  min_value?: number;
  max_value?: number;
}

export interface LogicAction {
  type: "jump_to" | "end_survey";
  target_question_id?: string;
}

export interface LogicRule {
  condition: LogicCondition;
  action: LogicAction;
}

export interface QuestionLogic {
  enabled: boolean;
  rules: LogicRule[];
}

// ---- 题目（第一阶段内嵌格式，仍用于编辑器内部状态） ----
export interface Question {
  question_id: string;
  type: "single_choice" | "multiple_choice" | "text_input" | "number_input";
  title: string;
  required: boolean;
  order: number;
  options?: QuestionOption[];
  validation?: QuestionValidation;
  logic?: QuestionLogic;
}

// ---- 第二阶段：问卷题目引用 ----
export interface SurveyQuestionRef {
  question_id: string;
  order: number;
  logic?: QuestionLogic;
  question_ref_id: string;
  version_number: number;
  // 以下字段由后端解析填充
  type?: string;
  title?: string;
  required?: boolean;
  options?: QuestionOption[];
  validation?: QuestionValidation;
}

// ---- 问卷 ----
export interface Survey {
  survey_id: string;
  title: string;
  description?: string;
  creator_id: string;
  access_code: string;
  status: "draft" | "published" | "closed";
  created_at: string;
  updated_at: string;
  deadline?: string;
  response_count: number;
  settings: SurveySettings;
  questions: SurveyQuestionRef[];
}


export interface SurveyListItem {
  survey_id: string;
  title: string;
  description?: string;
  status: "draft" | "published" | "closed";
  created_at: string;
  deadline?: string;
  response_count: number;
  access_code: string;
}

export interface SurveyListResponse {
  total: number;
  page: number;
  page_size: number;
  surveys: SurveyListItem[];
}

// ---- 公开问卷（填写端） ----
export interface PublicSurvey {
  survey_id: string;
  title: string;
  description?: string;
  access_code: string;
  settings: SurveySettings;
  deadline?: string;
  questions: SurveyQuestionRef[];
  has_submitted?: boolean;
  allow_multiple?: boolean;
}

// ---- 答案 ----
export interface Answer {
  question_id: string;
  answer: string | string[] | number;
}

export interface SubmitResponseRequest {
  survey_id: string;
  access_code: string;
  answers: Answer[];
  is_anonymous?: boolean;
  completion_time?: number;
}

export interface SubmitResponseResult {
  response_id: string;
  survey_id: string;
  submitted_at: string;
}

// ---- 答卷列表（创建者查看） ----
export interface ResponseListItem {
  response_id: string;
  respondent_id: string | null;
  is_anonymous: boolean;
  respondent_name: string | null;
  submitted_at: string;
  completion_time: number | null;
}

// ---- 统计 ----
export interface OptionStatistic {
  option_id: string;
  text: string;
  count: number;
  percentage: number;
  respondents?: OptionRespondent[];
}

export interface OptionRespondent {
  respondent_id: string | null;
  display_name: string;
  is_anonymous: boolean;
}

export interface NumberStatistics {
  average: number;
  min: number;
  max: number;
  values: number[];
}

export interface QuestionStatistic {
  question_id: string;
  title: string;
  type: string;
  total_answers: number;
  option_statistics?: OptionStatistic[];
  text_responses?: string[];
  number_statistics?: NumberStatistics;
}

export interface SurveyStatistics {
  survey_id: string;
  survey_title: string;
  total_responses: number;
  question_statistics: QuestionStatistic[];
}

// ---- 创建问卷请求 ----
export interface CreateSurveyRequest {
  title: string;
  description?: string;
  settings?: SurveySettings;
  deadline?: string;
}

export interface UpdateSurveyRequest {
  title?: string;
  description?: string;
  settings?: SurveySettings;
  deadline?: string;
  questions?: SurveyQuestionRef[];
}

// ============ 第二阶段新增：题目域类型 ============

// ---- 题目版本 ----
export interface QuestionVersion {
  version_number: number;
  created_at: string;
  updated_by: string;
  parent_version_number: number | null;
  type: string;
  title: string;
  options?: QuestionOption[];
  validation?: QuestionValidation;
}

// ---- 题目详情 ----
export interface QuestionDetail {
  question_id: string;
  latest_version_number: number;
  creator: string;
  shared_with: string[];
  banked_by: string[];
  versions: QuestionVersion[];
}

// ---- 题目列表项 ----
export interface QuestionListItem {
  question_id: string;
  latest_version_number: number;
  creator: string;
  latest_title: string;
  latest_type: string;
  created_at: string;
}

// ---- 题目使用情况 ----
export interface QuestionUsageItem {
  survey_id: string;
  survey_title: string;
  survey_status: string;
  version_number: number;
}

// ---- 题目创建/新版本请求 ----
export interface CreateQuestionRequest {
  type: string;
  title: string;
  options?: QuestionOption[];
  validation?: QuestionValidation;
}

export interface CreateVersionRequest {
  type: string;
  title: string;
  options?: QuestionOption[];
  validation?: QuestionValidation;
  parent_version_number?: number;
}

// ---- 跨问卷单题统计 ----
export interface CrossSurveyVersionStat {
  version_number: number;
  title: string;
  type: string;
  total_answers: number;
  survey_count: number;
  option_statistics?: OptionStatistic[];
  text_responses?: string[];
  number_statistics?: NumberStatistics;
}

export interface CrossSurveyQuestionStatistics {
  question_ref_id: string;
  question_title: string;
  question_type: string;
  total_answers: number;
  survey_count: number;
  surveys: { survey_id: string; title: string; status: string }[];
  version_statistics: CrossSurveyVersionStat[];
}
