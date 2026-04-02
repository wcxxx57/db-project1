import { useMemo, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AuthModal from "./components/AuthModal";
import Dashboard from "./pages/Dashboard";
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

  if (!isLoggedIn) {
    return <AuthModal onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        {/* Redirect root to dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
