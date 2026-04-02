import { useMemo, useState, useCallback } from "react";
import {BrowserRouter,Routes,Route,Navigate,useNavigate,useParams,} from "react-router-dom";
import AuthModal from "./components/AuthModal";
import Dashboard from "./pages/Dashboard";
import SurveyFill from "./components/SurveyFill";
import SurveyEditor from "./components/SurveyEditor";
import StatisticsView from "./components/StatisticsView";
import { AUTH_TOKEN_KEY, AUTH_USER_KEY } from "./services/api";
import type { LoginResponse, UserInfo } from "./types";
import "./App.css";

function SurveyFillRoute() {
  const navigate = useNavigate();
  const { accessCode } = useParams<{ accessCode: string }>();

  if (!accessCode) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <SurveyFill
      accessCode={accessCode}
      onBack={() => navigate("/dashboard")}
    />
  );
}

function StatisticsRoute() {
  const navigate = useNavigate();
  const { surveyId } = useParams<{ surveyId: string }>();

  if (!surveyId) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <StatisticsView
      surveyId={surveyId}
      onBack={() => navigate("/dashboard")}
    />
  );
}

function SurveyEditorRoute() {
  const navigate = useNavigate();
  const { surveyId } = useParams<{ surveyId: string }>();

  if (!surveyId) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <SurveyEditor
      surveyId={surveyId}
      onBack={() => navigate("/dashboard")}
    />
  );
}

function getStoredUser(): UserInfo | null {
  const raw = localStorage.getItem(AUTH_USER_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as UserInfo;
  } catch {
    return null;
  }
}

export default function App() {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem(AUTH_TOKEN_KEY),
  );
  const [user, setUser] = useState<UserInfo | null>(getStoredUser());

  const isLoggedIn = useMemo(() => Boolean(token && user), [token, user]);

  const handleLoginSuccess = useCallback((payload: LoginResponse) => {
    localStorage.setItem(AUTH_TOKEN_KEY, payload.access_token);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(payload.user));
    setToken(payload.access_token);
    setUser(payload.user);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        {/* =======================
            受保护路由：必须登录
            ======================= */}
            
        {/* 填写问卷页面：点链接进来，未登录直接弹登录框 */}
        <Route
          path="/s/:accessCode"
          element={
            isLoggedIn ? (
              <SurveyFillRoute />
            ) : (
              <AuthModal onLoginSuccess={handleLoginSuccess} />
            )
          }
        />

        {/* 仪表盘（我的问卷列表） */}
        <Route
          path="/dashboard"
          element={
            isLoggedIn ? (
              <Dashboard />
            ) : (
              <AuthModal onLoginSuccess={handleLoginSuccess} />
            )
          }
        />

        {/* 问卷统计页面 */}
        <Route
          path="/statistics/:surveyId"
          element={
            isLoggedIn ? (
              <StatisticsRoute />
            ) : (
              <AuthModal onLoginSuccess={handleLoginSuccess} />
            )
          }
        />

        {/* 问卷编辑页面 */}
        <Route
          path="/editor/:surveyId"
          element={
            isLoggedIn ? (
              <SurveyEditorRoute />
            ) : (
              <AuthModal onLoginSuccess={handleLoginSuccess} />
            )
          }
        />

        {/* 默认重定向：访问根目录或其他未知路径，统统去仪表盘 */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}