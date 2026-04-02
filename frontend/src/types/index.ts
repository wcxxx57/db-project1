export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

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

export interface Survey {
  survey_id: string;
  title: string;
  description: string;
  status: "draft" | "published" | "closed";
  access_code: string | null;
  response_count: number;
  created_at: string;
  deadline: string | null;
  is_anonymous: boolean;
}

export interface GetSurveysResponse {
  total: number;
  page: number;
  page_size: number;
  surveys: Survey[];
}

export interface CreateSurveyRequest {
  title: string;
  description?: string;
}
