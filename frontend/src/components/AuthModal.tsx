import { useMemo, useState, useRef, useCallback } from "react";
import { login, register } from "../services/api";
import type { LoginResponse } from "../types";

type AuthMode = "login" | "register";

interface AuthModalProps {
  onLoginSuccess: (payload: LoginResponse) => void;
}

function getPasswordStrength(pwd: string): {
  level: number;
  text: string;
  color: string;
} {
  if (!pwd) return { level: 0, text: "", color: "" };
  let score = 0;
  if (pwd.length >= 8) score++;
  if (pwd.length >= 10) score++;
  if (/[A-Z]/.test(pwd)) score++;
  if (/[0-9]/.test(pwd)) score++;
  if (/[^A-Za-z0-9]/.test(pwd)) score++;

  if (score <= 2) return { level: 1, text: "弱", color: "#E07A5F" };
  if (score <= 3) return { level: 2, text: "中等", color: "#E89B6C" };
  return { level: 3, text: "强", color: "#6B9B5A" };
}

export default function AuthModal({ onLoginSuccess }: AuthModalProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPwd, setShowConfirmPwd] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [shakeError, setShakeError] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);
  const submitLockRef = useRef(false);

  const title = useMemo(
    () =>
      mode === "login"
        ? "欢迎回来，继续管理您的问卷"
        : "创建账号，开始设计您的第一份问卷",
    [mode],
  );

  const pwdStrength = useMemo(
    () =>
      mode === "register"
        ? getPasswordStrength(password)
        : { level: 0, text: "", color: "" },
    [password, mode],
  );

  const switchMode = useCallback((newMode: AuthMode) => {
    setMode(newMode);
    setErrorMessage(null);
    setPassword("");
    setConfirmPwd("");
    setShowPassword(false);
    setShowConfirmPwd(false);
  }, []);

  const triggerError = useCallback((msg: string) => {
    setErrorMessage(msg);
    setShakeError(true);
    setTimeout(() => setShakeError(false), 400);
  }, []);

  const handleSubmit = useCallback(async () => {
    // Use a synchronous lock to block click/enter double-trigger races.
    if (submitLockRef.current) {
      return;
    }

    const normalizedUsername = username.trim();

    if (!normalizedUsername || !password.trim()) {
      triggerError("用户名和密码不能为空");
      return;
    }

    if (mode === "register") {
      if (normalizedUsername.length < 2) {
        triggerError("用户名不足2位，请至少输入2位");
        return;
      }
      if (normalizedUsername.length > 50) {
        triggerError("用户名超过50位，请输入不超过50位");
        return;
      }
      if (password.length < 8) {
        triggerError("密码不足8位，请至少输入8位");
        return;
      }
      if (password !== confirmPwd) {
        triggerError("两次密码输入不一致");
        return;
      }
    }

    submitLockRef.current = true;
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      if (mode === "login") {
        const loginData = await login({
          username: normalizedUsername,
          password,
        });
        onLoginSuccess(loginData);
      } else {
        await register({
          username: normalizedUsername,
          password,
        });
        setErrorMessage("✅ 注册成功！请登录");
        switchMode("login");
      }
    } catch (error: any) {
      triggerError(error.message || "请求失败");
    } finally {
      setIsSubmitting(false);
      submitLockRef.current = false;
    }
  }, [
    username,
    password,
    confirmPwd,
    mode,
    triggerError,
    switchMode,
    onLoginSuccess,
  ]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !isSubmitting) {
        handleSubmit();
      }
    },
    [handleSubmit, isSubmitting],
  );

  return (
    <div className="auth-overlay">
      <div className="blob blob-orange" />
      <div className="blob blob-blue" />
      <div className="blob blob-yellow" />

      <div className="auth-card">
        <div className="accent-bar" />

        <div className="card-content">
          <div className="brand-icon">🔑</div>

          <div className="auth-header">
            <h2 className="auth-title">云问卷</h2>
            <p className="auth-subtitle">{title}</p>
          </div>

          <div className="tab-container">
            <div className="tab-slider" data-mode={mode} />
            <button
              type="button"
              className="tab-btn"
              data-active={mode === "login" ? "true" : "false"}
              onClick={() => switchMode("login")}
            >
              登录
            </button>
            <button
              type="button"
              className="tab-btn"
              data-active={mode === "register" ? "true" : "false"}
              onClick={() => switchMode("register")}
            >
              注册
            </button>
          </div>

          {errorMessage && (
            <div
              ref={errorRef}
              className={`error-box ${shakeError ? "shake-anim" : ""}`}
              style={{
                background: errorMessage.includes("✅")
                  ? "var(--success-bg)"
                  : "var(--warn-bg)",
                color: errorMessage.includes("✅")
                  ? "var(--success-text)"
                  : "var(--warn-text)",
                borderLeftColor: errorMessage.includes("✅")
                  ? "var(--success-text)"
                  : "var(--warn-text)",
              }}
            >
              <span className="error-icon">
                {errorMessage.includes("✅") ? "✅" : "⚠️"}
              </span>
              <span>{errorMessage}</span>
            </div>
          )}

          <div className="form-group">
            <div className="input-wrapper">
              <span className="input-icon" style={{ left: 16 }}>
                🪪
              </span>
              <input
                className="auth-input"
                type="text"
                placeholder="请输入用户名"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onKeyDown={handleKeyDown}
              />
            </div>

            <div className="input-wrapper">
              <span className="input-icon" style={{ left: 16 }}>
                🔒
              </span>
              <input
                className="auth-input"
                type={showPassword ? "text" : "password"}
                placeholder="请输入密码"
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <button
                type="button"
                className="pwd-toggle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                title={showPassword ? "隐藏密码" : "显示密码"}
              >
                {showPassword ? "🙈" : "👁️"}
              </button>
            </div>

            {mode === "register" && password.length > 0 && (
              <>
                <div className="strength-bar">
                  <div
                    className="strength-segment"
                    style={
                      pwdStrength.level >= 1
                        ? { background: pwdStrength.color }
                        : {}
                    }
                  />
                  <div
                    className="strength-segment"
                    style={
                      pwdStrength.level >= 2
                        ? { background: pwdStrength.color }
                        : {}
                    }
                  />
                  <div
                    className="strength-segment"
                    style={
                      pwdStrength.level >= 3
                        ? { background: pwdStrength.color }
                        : {}
                    }
                  />
                </div>
                <span
                  className="strength-text"
                  style={{ color: pwdStrength.color }}
                >
                  密码强度：{pwdStrength.text}
                </span>
              </>
            )}

            {mode === "register" && (
              <div
                className="input-wrapper"
                style={{
                  animation: "fadeInUp 0.3s ease both",
                }}
              >
                <span className="input-icon" style={{ left: 16 }}>
                  🔐
                </span>
                <input
                  className="auth-input"
                  type={showConfirmPwd ? "text" : "password"}
                  placeholder="请再次输入密码"
                  autoComplete="new-password"
                  value={confirmPwd}
                  onChange={(e) => setConfirmPwd(e.target.value)}
                  onKeyDown={handleKeyDown}
                />
                <button
                  type="button"
                  className="pwd-toggle"
                  onClick={() => setShowConfirmPwd(!showConfirmPwd)}
                  tabIndex={-1}
                  title={showConfirmPwd ? "隐藏密码" : "显示密码"}
                >
                  {showConfirmPwd ? "🙈" : "👁️"}
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            className="submit-btn"
            disabled={isSubmitting}
            onClick={handleSubmit}
          >
            {isSubmitting && <div className="btn-spinner" />}
            {isSubmitting
              ? "处理中..."
              : mode === "login"
                ? "🚀 立即登录"
                : "🚀 立即注册"}
          </button>

          <div className="auth-divider">
            <span className="divider-text">or</span>
          </div>

          <div className="auth-footer">
            {mode === "login" ? (
              <span>
                还没有账号？{" "}
                <a onClick={() => switchMode("register")}>立即注册</a>
              </span>
            ) : (
              <span>
                已有账号？ <a onClick={() => switchMode("login")}>立即登录</a>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
