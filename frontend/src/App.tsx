import { useMemo, useState } from "react";
import AuthModal from "./components/AuthModal";
import { AUTH_TOKEN_KEY, AUTH_USER_KEY } from "./services/api";
import type { LoginResponse, UserInfo } from "./types";
import "./App.css";

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

  const handleLoginSuccess = (payload: LoginResponse) => {
    localStorage.setItem(AUTH_TOKEN_KEY, payload.access_token);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(payload.user));
    setToken(payload.access_token);
    setUser(payload.user);
  };

  const logout = () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    setToken(null);
    setUser(null);
  };

  if (!isLoggedIn) {
    return <AuthModal onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <main className="dashboard-shell">
      <section className="dashboard-card">
        <h2>登录成功</h2>
        <p>当前用户：{user?.username}</p>
        <p>后续将从这里接入问卷创建、填写与统计模块。</p>
        <button className="logout-btn" onClick={logout}>
          退出登录
        </button>
      </section>
    </main>
  );
}
