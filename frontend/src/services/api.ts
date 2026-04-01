import axios, { AxiosError } from "axios";
import type {
  ApiResponse,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  UserInfo,
} from "../types";

export const AUTH_TOKEN_KEY = "survey_auth_token";
export const AUTH_USER_KEY = "survey_auth_user";

const ERROR_MESSAGE_MAP: Record<number, string> = {
  1001: "用户名已存在，请更换后重试",
  1002: "用户名或密码错误，请检查后重试",
  1004: "未发现该用户，请先注册后再登录",
  1003: "登录状态已失效，请重新登录",
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
