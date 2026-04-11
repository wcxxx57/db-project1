import axios, { AxiosError } from "axios";
import type {
  ApiResponse,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  UserInfo,
  SurveyListResponse,
  Survey,
  CreateSurveyRequest,
  UpdateSurveyRequest,
  PublicSurvey,
  SubmitResponseRequest,
  SubmitResponseResult,
  ResponseListItem,
  SurveyStatistics,
  QuestionStatistic,
  QuestionListItem,
  QuestionDetail,
  QuestionVersion,
  QuestionUsageItem,
  CreateQuestionRequest,
  CreateVersionRequest,
  CrossSurveyQuestionStatistics,
} from "../types";

export const AUTH_TOKEN_KEY = "survey_auth_token";
export const AUTH_USER_KEY = "survey_auth_user";

const ERROR_MESSAGE_MAP: Record<number, string> = {
  1001: "用户名已存在，请更换后重试",
  1002: "用户名或密码错误，请检查后重试",
  1004: "未发现该用户，请先注册后再登录",
  1003: "登录状态已失效，请重新登录",
  2001: "问卷不存在",
  2002: "无权限操作该问卷",
  2003: "问卷已关闭",
  2004: "问卷已过期",
  2005: "访问码无效",
  3001: "答案校验失败",
  3002: "您已经提交过该问卷，不允许重复提交",
  3003: "必填题未回答",
  3004: "请先登录后再填写问卷",
  // 第二阶段新增
  4001: "题目不存在",
  4002: "题目版本不存在",
  4003: "题目正在被已发布问卷使用，无法删除",
  4004: "共享目标用户不存在",
};

class ApiBusinessError extends Error {
  code: number;

  constructor(code: number, message: string) {
    super(message);
    this.code = code;
    this.name = "ApiBusinessError";
  }
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function parseApiResponse<T>(payload: ApiResponse<T>): T {
  if (payload.code !== 0) {
    throw new ApiBusinessError(payload.code, payload.message || "请求失败");
  }
  return payload.data;
}

function normalizeError(error: unknown): Error {
  if (error instanceof ApiBusinessError) {
    return error;
  }

  if (error instanceof AxiosError) {
    const responseData = error.response?.data as ApiResponse<null> | undefined;
    if (responseData && typeof responseData.code === "number") {
      const friendlyMessage =
        responseData.message ||
        ERROR_MESSAGE_MAP[responseData.code] ||
        "请求失败";
      return new ApiBusinessError(responseData.code, friendlyMessage);
    }
    return new Error("网络错误，请检查后端服务是否已启动");
  }

  return new Error("未知错误，请稍后重试");
}

// ============ 认证 ============

export async function register(payload: RegisterRequest): Promise<UserInfo> {
  try {
    const response = await apiClient.post<ApiResponse<UserInfo>>(
      "/auth/register",
      payload,
    );
    return parseApiResponse(response.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  try {
    const response = await apiClient.post<ApiResponse<LoginResponse>>(
      "/auth/login",
      payload,
    );
    return parseApiResponse(response.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

// ============ 问卷管理 ============

export async function createSurvey(
  payload: CreateSurveyRequest,
): Promise<{ survey_id: string; status: string; access_code: string; created_at: string }> {
  try {
    const resp = await apiClient.post<ApiResponse<any>>("/surveys", payload);
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getMySurveys(
  page = 1,
  pageSize = 20,
): Promise<SurveyListResponse> {
  try {
    const resp = await apiClient.get<ApiResponse<SurveyListResponse>>(
      "/surveys/my",
      { params: { page, page_size: pageSize } },
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getSurveyDetail(surveyId: string): Promise<Survey> {
  try {
    const resp = await apiClient.get<ApiResponse<Survey>>(
      `/surveys/${surveyId}`,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function publishSurvey(surveyId: string): Promise<Survey> {
  try {
    const response = await apiClient.post<ApiResponse<Survey>>(
      `/surveys/${surveyId}/publish`,
    );
    return parseApiResponse(response.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function closeSurvey(surveyId: string): Promise<Survey> {
  try {
    const response = await apiClient.post<ApiResponse<Survey>>(
      `/surveys/${surveyId}/close`,
    );
    return parseApiResponse(response.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function deleteSurvey(surveyId: string): Promise<void> {
  try {
    const resp = await apiClient.delete<ApiResponse<null>>(
      `/surveys/${surveyId}`,
    );
    parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function updateSurvey(
  surveyId: string,
  payload: UpdateSurveyRequest,
): Promise<Survey> {
  try {
    const resp = await apiClient.put<ApiResponse<Survey>>(
      `/surveys/${surveyId}`,
      payload,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

// ============ 公开问卷（填写端） ============

export async function getPublicSurvey(
  accessCode: string,
): Promise<PublicSurvey> {
  try {
    const resp = await apiClient.get<ApiResponse<PublicSurvey>>(
      `/public/surveys/${accessCode}`,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

// ============ 提交答卷 ============

export async function submitResponse(
  payload: SubmitResponseRequest,
): Promise<SubmitResponseResult> {
  try {
    const resp = await apiClient.post<ApiResponse<SubmitResponseResult>>(
      "/responses",
      payload,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

// ============ 统计 ============

export async function getSurveyStatistics(
  surveyId: string,
): Promise<SurveyStatistics> {
  try {
    const resp = await apiClient.get<ApiResponse<SurveyStatistics>>(
      `/surveys/${surveyId}/statistics`,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getQuestionStatistics(
  surveyId: string,
  questionId: string,
): Promise<QuestionStatistic> {
  try {
    const resp = await apiClient.get<ApiResponse<QuestionStatistic>>(
      `/surveys/${surveyId}/questions/${questionId}/statistics`,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

// ============ 答卷列表 ============

export async function getResponseList(
  surveyId: string,
): Promise<ResponseListItem[]> {
  try {
    const resp = await apiClient.get<ApiResponse<ResponseListItem[]>>(
      `/surveys/${surveyId}/responses`,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

// ============ 第二阶段新增：题目管理 ============

export async function createQuestion(
  payload: CreateQuestionRequest,
): Promise<{ question_id: string; version_number: number; created_at: string }> {
  try {
    const resp = await apiClient.post<ApiResponse<any>>("/questions", payload);
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getMyQuestions(): Promise<QuestionListItem[]> {
  try {
    const resp = await apiClient.get<ApiResponse<QuestionListItem[]>>("/questions/my");
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getSharedQuestions(): Promise<QuestionListItem[]> {
  try {
    const resp = await apiClient.get<ApiResponse<QuestionListItem[]>>("/questions/shared");
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getBankedQuestions(): Promise<QuestionListItem[]> {
  try {
    const resp = await apiClient.get<ApiResponse<QuestionListItem[]>>("/questions/bank");
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getQuestionDetail(questionId: string): Promise<QuestionDetail> {
  try {
    const resp = await apiClient.get<ApiResponse<QuestionDetail>>(`/questions/${questionId}`);
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function createNewVersion(
  questionId: string,
  payload: CreateVersionRequest,
): Promise<{ question_id: string; version_number: number; created_at: string }> {
  try {
    const resp = await apiClient.post<ApiResponse<any>>(`/questions/${questionId}/versions`, payload);
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function updateVersion(
  questionId: string,
  versionNumber: number,
  payload: CreateVersionRequest,
): Promise<{ question_id: string; version_number: number; updated_at: string; mode: string }> {
  try {
    const resp = await apiClient.put<ApiResponse<any>>(
      `/questions/${questionId}/versions/${versionNumber}`,
      payload,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getVersionHistory(
  questionId: string,
): Promise<QuestionVersion[]> {
  try {
    const resp = await apiClient.get<ApiResponse<QuestionVersion[]>>(`/questions/${questionId}/versions`);
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function restoreVersion(
  questionId: string,
  versionNumber: number,
): Promise<{ question_id: string; version_number: number; created_at: string }> {
  try {
    const resp = await apiClient.post<ApiResponse<any>>(
      `/questions/${questionId}/versions/${versionNumber}/restore`,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function shareQuestion(
  questionId: string,
  username: string,
): Promise<{ message: string }> {
  try {
    const resp = await apiClient.post<ApiResponse<any>>(`/questions/${questionId}/share`, { username });
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function unshareQuestion(
  questionId: string,
  username: string,
): Promise<{ message: string }> {
  try {
    const resp = await apiClient.post<ApiResponse<any>>(`/questions/${questionId}/unshare`, { username });
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function addToBank(questionId: string): Promise<{ message: string }> {
  try {
    const resp = await apiClient.post<ApiResponse<any>>(`/questions/${questionId}/bank`);
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function removeFromBank(questionId: string): Promise<{ message: string }> {
  try {
    const resp = await apiClient.delete<ApiResponse<any>>(`/questions/${questionId}/bank`);
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getQuestionUsage(questionId: string): Promise<QuestionUsageItem[]> {
  try {
    const resp = await apiClient.get<ApiResponse<QuestionUsageItem[]>>(`/questions/${questionId}/usage`);
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function deleteQuestion(questionId: string): Promise<void> {
  try {
    const resp = await apiClient.delete<ApiResponse<null>>(`/questions/${questionId}`);
    parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function getCrossSurveyStats(
  questionRefId: string,
): Promise<CrossSurveyQuestionStatistics> {
  try {
    const resp = await apiClient.get<ApiResponse<CrossSurveyQuestionStatistics>>(
      `/questions/${questionRefId}/cross-statistics`,
    );
    return parseApiResponse(resp.data);
  } catch (error) {
    throw normalizeError(error);
  }
}
