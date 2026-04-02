import { useCallback, useEffect, useState } from "react";
import type { SurveyListItem } from "../types";
import { getMySurveys, createSurvey, publishSurvey, closeSurvey, deleteSurvey } from "../services/api";

interface DashboardProps {
  username: string;
  onLogout: () => void;
  onEditSurvey: (surveyId: string) => void;
  onViewStats: (surveyId: string) => void;
  onFillSurvey: (accessCode: string) => void;
}

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: "草稿", color: "var(--brown-medium)" },
  published: { label: "已发布", color: "#478211" },
  closed: { label: "已关闭", color: "var(--warn-text)" },
};

export default function Dashboard({
  username,
  onLogout,
  onEditSurvey,
  onViewStats,
  onFillSurvey,
}: DashboardProps) {
  const [surveys, setSurveys] = useState<SurveyListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [fillCode, setFillCode] = useState("");

  const loadSurveys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMySurveys(1, 50);
      setSurveys(data.surveys);
    } catch (e: any) {
      setError(e.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSurveys();
  }, [loadSurveys]);

  const handleCreate = useCallback(async () => {
    setCreating(true);
    try {
      const result = await createSurvey({ title: "未命名问卷" });
      onEditSurvey(result.survey_id);
    } catch (e: any) {
      setError(e.message || "创建失败");
    } finally {
      setCreating(false);
    }
  }, [onEditSurvey]);

  const handlePublish = useCallback(
    async (id: string) => {
      try {
        await publishSurvey(id);
        loadSurveys();
      } catch (e: any) {
        setError(e.message);
      }
    },
    [loadSurveys],
  );

  const handleClose = useCallback(
    async (id: string) => {
      try {
        await closeSurvey(id);
        loadSurveys();
      } catch (e: any) {
        setError(e.message);
      }
    },
    [loadSurveys],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm("确定删除该问卷？此操作不可恢复。")) return;
      try {
        await deleteSurvey(id);
        loadSurveys();
      } catch (e: any) {
        setError(e.message);
      }
    },
    [loadSurveys],
  );

  const handleGoFill = useCallback(() => {
    const code = fillCode.trim();
    if (code) onFillSurvey(code);
  }, [fillCode, onFillSurvey]);

  return (
    <div className="dashboard-page">
      <div className="blob blob-orange" />
      <div className="blob blob-blue" />
      <div className="blob blob-yellow" />

      <div className="dashboard-container">
        {/* Header */}
        <div className="dash-header">
          <div className="dash-header-left">
            <div className="brand-icon-sm">📋</div>
            <div>
              <h1 className="dash-title">云问卷</h1>
              <p className="dash-subtitle">欢迎回来，{username}</p>
            </div>
          </div>
          <div className="dash-header-right">
            <div className="fill-input-group">
              <input
                className="fill-code-input"
                placeholder="输入访问码填写问卷"
                value={fillCode}
                onChange={(e) => setFillCode(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleGoFill()}
              />
              <button className="fill-go-btn" onClick={handleGoFill}>
                前往填写
              </button>
            </div>
            <button className="logout-btn-sm" onClick={onLogout}>
              退出
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="dash-actions">
          <button
            className="create-btn"
            disabled={creating}
            onClick={handleCreate}
          >
            {creating ? "创建中..." : "＋ 新建问卷"}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="error-box">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
            <button
              style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", fontWeight: 600 }}
              onClick={() => setError(null)}
            >
              ✕
            </button>
          </div>
        )}

        {/* List */}
        {loading ? (
          <div className="dash-loading">加载中…</div>
        ) : surveys.length === 0 ? (
          <div className="dash-empty">
            <p>还没有问卷，点击上方按钮创建第一份问卷吧 ✨</p>
          </div>
        ) : (
          <div className="survey-grid">
            {surveys.map((s) => {
              const st = STATUS_MAP[s.status] || STATUS_MAP.draft;
              return (
                <div key={s.survey_id} className="survey-card">
                  <div className="survey-card-top">
                    <span
                      className="status-badge"
                      style={{ color: st.color, borderColor: st.color }}
                    >
                      {st.label}
                    </span>
                    <span className="response-count">
                      {s.response_count} 份答卷
                    </span>
                  </div>
                  <h3 className="survey-card-title">{s.title}</h3>
                  {s.description && (
                    <p className="survey-card-desc">{s.description}</p>
                  )}
                  <div className="survey-card-meta">
                    <span>
                      创建于{" "}
                      {new Date(s.created_at).toLocaleDateString("zh-CN")}
                    </span>
                    {s.deadline && (
                      <span>
                        截止{" "}
                        {new Date(s.deadline).toLocaleDateString("zh-CN")}
                      </span>
                    )}
                  </div>
                  {/* 访问码 */}
                  {s.status === "published" && (
                    <div className="survey-card-code">
                      访问码：<strong>{s.access_code}</strong>
                      <button
                        className="copy-btn"
                        onClick={() => {
                          navigator.clipboard.writeText(s.access_code);
                        }}
                        title="复制访问码"
                      >
                        📋
                      </button>
                    </div>
                  )}
                  <div className="survey-card-actions">
                    {s.status !== "published" && (
                      <button
                        className="card-action-btn edit"
                        onClick={() => onEditSurvey(s.survey_id)}
                      >
                        编辑
                      </button>
                    )}
                    {(s.status === "draft" || s.status === "closed") && (
                      <button
                        className="card-action-btn publish"
                        onClick={() => handlePublish(s.survey_id)}
                      >
                        发布
                      </button>
                    )}
                    {s.status === "published" && (
                      <button
                        className="card-action-btn close-survey"
                        onClick={() => handleClose(s.survey_id)}
                      >
                        关闭
                      </button>
                    )}
                    {s.response_count > 0 && (
                      <button
                        className="card-action-btn stats"
                        onClick={() => onViewStats(s.survey_id)}
                      >
                        统计
                      </button>
                    )}
                    {s.status === "published" && (
                      <button
                        className="card-action-btn fill"
                        onClick={() => onFillSurvey(s.access_code)}
                      >
                        填写
                      </button>
                    )}
                    <button
                      className="card-action-btn delete"
                      onClick={() => handleDelete(s.survey_id)}
                    >
                      删除
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
