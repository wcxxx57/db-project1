import React, { useEffect, useState } from "react";
import {
  Plus,
  Edit2,
  Share2,
  BarChart2,
  Trash2,
  PowerOff,
  Loader2,
  XCircle,
  PlayCircle,
} from "lucide-react";
import {
  getMySurveys,
  createSurvey,
  publishSurvey,
  closeSurvey,
  deleteSurvey,
  AUTH_USER_KEY,
  AUTH_TOKEN_KEY,
} from "../services/api";
import type { SurveyListItem } from "../types";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const [surveys, setSurveys] = useState<SurveyListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [copyToast, setCopyToast] = useState<{
    visible: boolean;
    type: "success" | "error";
    title: string;
    message: string;
  }>({
    visible: false,
    type: "success",
    title: "",
    message: "",
  });
  const navigate = useNavigate();

  const userStr = localStorage.getItem(AUTH_USER_KEY);
  const user = userStr ? JSON.parse(userStr) : null;

  const fetchSurveys = async () => {
    setLoading(true);
    try {
      const res = await getMySurveys(1, 50);
      setSurveys(res.surveys);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSurveys();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    window.location.reload();
  };

  const handleCreate = async () => {
    setIsCreating(true);
    try {
      const result = await createSurvey({
        title: "未命名问卷",
        description: "点击编辑以修改详细内容",
      });
      navigate("/editor/" + result.survey_id);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsCreating(false);
    }
  };

  const handlePublish = async (surveyId: string) => {
    try {
      await publishSurvey(surveyId);
      fetchSurveys();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleClose = async (surveyId: string) => {
    try {
      await closeSurvey(surveyId);
      fetchSurveys();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDelete = async (surveyId: string) => {
    if (
      !window.confirm("确定要删除该问卷吗？删除后将无法恢复其中已收集的数据。")
    )
      return;
    try {
      await deleteSurvey(surveyId);
      fetchSurveys();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleCopyLink = async (accessCode: string | null) => {
    if (!accessCode) return;
    const url = window.location.origin + "/s/" + accessCode;
    try {
      await navigator.clipboard.writeText(url);
      setCopyToast({
        visible: true,
        type: "success",
        title: "复制成功",
        message: `问卷链接：${url}\n已复制到剪贴板，去群聊或聊天窗口粘贴分享吧。`,
      });
    } catch {
      setCopyToast({
        visible: true,
        type: "error",
        title: "复制失败",
        message: "请手动复制链接：" + url,
      });
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === "draft")
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 text-[13px] font-semibold rounded-full bg-[var(--yellow-light)] text-[var(--brown-dark)] shadow-sm">
          🟡 暂未发布
        </span>
      );
    if (status === "published")
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 text-[13px] font-semibold rounded-full bg-[var(--green-lighter)] text-[#1f4a3e] shadow-sm">
          🟢 收集中
        </span>
      );
    return (
      <span className="flex items-center gap-1.5 px-3 py-1 text-[13px] font-semibold rounded-full bg-[var(--warn-bg)] text-[var(--warn-text)] shadow-sm">
        🔴 已关闭
      </span>
    );
  };

  return (
    <div
      className="min-h-screen relative bg-[var(--bg-canvas)] overflow-x-hidden flex flex-col font-sans"
      style={
        {
          animation: "fadeIn 0.5s ease",
          // 锁定 Dashboard 的蓝色系（保持现在的颜色）
          "--blue": "#5ba3d0",
          "--blue-light": "#7eb8d9",
          "--blue-lighter": "#c5dce9",
          "--blue-mist": "#e9f2f8",
        } as React.CSSProperties
      }
    >
      {copyToast.visible && (
        <div className="dashboard-center-toast-mask" role="dialog" aria-modal="true">
          <div className={`dashboard-center-toast dashboard-center-toast-${copyToast.type}`}>
            <div className="dashboard-center-toast-head">
              <strong>{copyToast.title}</strong>
              <button
                type="button"
                className="dashboard-center-toast-close"
                onClick={() =>
                  setCopyToast((prev) => ({
                    ...prev,
                    visible: false,
                  }))
                }
                aria-label="关闭弹窗"
              >
                ×
              </button>
            </div>
            <p>{copyToast.message}</p>
          </div>
        </div>
      )}

      {/* Background Ornaments - Hidden */}
      <div
        className="fixed inset-0 pointer-events-none overflow-hidden z-0"
        style={{ display: "none" }}
      >
        <div className="blob blob-orange"></div>
        <div className="blob blob-blue"></div>
      </div>

      {/* Top Navbar */}
      <header className="relative z-10 w-full h-20 bg-gradient-to-r from-[#fff4cc] to-[#ffd9a8] backdrop-blur-md border-b border-[#ffc080]/30 px-10 flex justify-between items-center shadow-sm">
        <div className="flex items-center gap-4">
          <div className="text-3xl">📋</div>
          <h1 className="text-2xl font-black text-[var(--brown-deep)] tracking-tight">
            线上问卷系统
          </h1>
        </div>
        <div className="flex items-center gap-12">
          <span className="text-lg font-bold text-[var(--brown-dark)]">
            欢迎, {user?.username || ""} 👋
          </span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-6 py-1.5 text-base font-bold text-white bg-[var(--warn-text)] rounded-lg hover:bg-[#a63018] transition-all duration-200 hover:scale-105 shadow-md ml-auto"
          >
            <PowerOff size={16} />
            退出登录
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="relative z-10 flex-1 w-full max-w-5xl mx-auto px-8 py-16 flex flex-col">
        {/* Create Button */}
        <button
          onClick={handleCreate}
          disabled={isCreating}
          className="main-create-btn flex items-center justify-center gap-3 px-12 py-5 w-full sm:w-auto text-xl font-extrabold text-[var(--brown-deep)] mb-16 mx-auto"
        >
          {isCreating ? (
            <Loader2 className="animate-spin" size={28} />
          ) : (
            <Plus size={28} className="stroke-[2.5]" />
          )}
          <span>创建新问卷</span>
        </button>

        {/* Survey List Header */}
        <div className="w-full mb-8">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📋</span>
            <h2 className="text-3xl font-black text-[var(--brown-deep)] tracking-tight">
              我的问卷列表
            </h2>
            <span className="ml-auto text-base font-bold text-[var(--brown-deep)] bg-gradient-to-r from-[var(--yellow)] to-[var(--orange)] px-4 py-1 rounded-full shadow-md">
              共 {surveys.length} 份
            </span>
          </div>
        </div>

        {/* Surveys List */}
        <div className="w-full flex flex-col gap-5 pb-20">
          {loading ? (
            <div className="flex flex-col justify-center items-center py-24 text-[var(--brown-medium)]">
              <Loader2 className="animate-spin w-12 h-12 mb-4" />
              <span className="text-lg font-semibold">数据加载中...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-3 p-5 bg-[var(--warn-bg)] text-[var(--warn-text)] font-semibold rounded-2xl border-l-4 border-[var(--warn-text)]">
              <XCircle size={22} className="flex-shrink-0" />
              <span>{error}</span>
            </div>
          ) : surveys.length === 0 ? (
            <div className="py-24 text-center">
              <div className="text-7xl mb-6 opacity-40">📂</div>
              <p className="text-xl font-bold text-[var(--brown-light)]">
                暂无问卷，请点击上方按钮创建新问卷
              </p>
            </div>
          ) : (
            surveys.map((survey) => (
              <div key={survey.survey_id} className="survey-card">
                {/* Title Section */}
                <div className="px-7 pt-7 pb-0">
                  <div className="flex items-start gap-3 mb-4">
                    <span className="text-3xl flex-shrink-0">📝</span>
                    <h3 className="text-2xl font-bold text-[var(--brown-deep)] leading-tight break-words flex-1">
                      {survey.title}
                    </h3>
                  </div>
                </div>

                {/* Divider */}
                <div className="px-7 py-4">
                  <div className="h-px bg-gradient-to-r from-[var(--brown-light)]/10 via-[var(--brown-light)]/25 to-[var(--brown-light)]/10"></div>
                </div>

                {/* Status Section */}
                <div className="px-7 pb-6">
                  <div className="flex items-center gap-4 flex-wrap">
                    {getStatusBadge(survey.status)}
                    <span className="text-sm font-bold text-[var(--brown-medium)] bg-[var(--bg-canvas)] px-4 py-2 rounded-lg">
                      📊 {survey.response_count || 0} 份答卷
                    </span>
                  </div>
                </div>

                {/* Divider */}
                <div className="px-7 py-0">
                  <div className="h-px bg-gradient-to-r from-[var(--brown-light)]/10 via-[var(--brown-light)]/25 to-[var(--brown-light)]/10"></div>
                </div>

                {/* Action Buttons Section */}
                <div className="px-7 py-6 flex flex-wrap gap-3 items-center">
                  <button
                    className="action-chip action-chip-orange"
                    onClick={() => navigate("/editor/" + survey.survey_id)}
                  >
                    <Edit2 size={18} />
                    <span>编辑问卷</span>
                  </button>

                  {survey.status === "draft" || survey.status === "closed" ? (
                    <button
                      className="action-chip action-chip-blue"
                      onClick={() => handlePublish(survey.survey_id)}
                    >
                      <PlayCircle size={18} />
                      <span>发布问卷</span>
                    </button>
                  ) : (
                    <button
                      className="action-chip action-chip-green"
                      onClick={() => handleCopyLink(survey.access_code)}
                    >
                      <Share2 size={18} />
                      <span>分享链接</span>
                    </button>
                  )}

                  <button
                    className="action-chip action-chip-purple"
                    onClick={() => navigate("/statistics/" + survey.survey_id)}
                  >
                    <BarChart2 size={18} />
                    <span>查看统计</span>
                  </button>

                  <div className="flex-1"></div>

                  {survey.status === "published" ? (
                    <button
                      className="action-chip action-chip-red"
                      onClick={() => handleClose(survey.survey_id)}
                    >
                      <XCircle size={18} />
                      <span>关闭问卷</span>
                    </button>
                  ) : (
                    <button
                      className="action-chip action-chip-red"
                      onClick={() => handleDelete(survey.survey_id)}
                    >
                      <Trash2 size={18} />
                      <span>删除问卷</span>
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
