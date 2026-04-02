import { useCallback, useEffect, useState } from "react";
import type {
  SurveyStatistics,
  QuestionStatistic,
  ResponseListItem,
  OptionStatistic,
} from "../types";
import { getSurveyStatistics, getResponseList } from "../services/api";

interface StatisticsViewProps {
  surveyId: string;
  onBack: () => void;
}

function OptionStatsWithDropdown({ options }: { options: OptionStatistic[] }) {
  const [expandedOptionId, setExpandedOptionId] = useState<string | null>(null);
  const maxVal = Math.max(...options.map((i) => i.count), 1);

  return (
    <div className="bar-chart">
      {options.map((option) => {
        const isExpanded = expandedOptionId === option.option_id;
        const respondents = option.respondents || [];

        return (
          <div key={option.option_id}>
            <div className="bar-row">
              <span className="bar-label">{option.text}</span>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{ width: `${(option.count / maxVal) * 100}%` }}
                />
              </div>
              <span className="bar-value">
                {option.count} ({option.percentage}%)
              </span>
              <button
                type="button"
                onClick={() =>
                  setExpandedOptionId((prev) => (prev === option.option_id ? null : option.option_id))
                }
                style={{
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: 14,
                  color: "var(--brown-medium)",
                  padding: "0 4px",
                }}
                aria-label={`查看选项 ${option.text} 的用户`}
                title={`查看选项 ${option.text} 的用户`}
              >
                {isExpanded ? "▼" : "▶"}
              </button>
            </div>

            {isExpanded && (
              <div style={{ margin: "4px 0 10px 4px" }}>
                {respondents.length === 0 ? (
                  <p className="no-data" style={{ margin: 0 }}>暂无用户</p>
                ) : (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {respondents.map((user, idx) => (
                      <span
                        key={`${option.option_id}-${idx}-${user.respondent_id || "anon"}`}
                        style={{
                          fontSize: 12,
                          padding: "4px 10px",
                          borderRadius: 999,
                          background: user.is_anonymous ? "#f8f0e6" : "#e8f2fb",
                          color: "var(--brown-dark)",
                          border: "1px solid var(--brown-light)",
                        }}
                      >
                        {user.is_anonymous ? "匿名用户" : user.display_name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function QuestionStatCard({ stat }: { stat: QuestionStatistic }) {
  return (
    <div className="stat-card">
      <div className="stat-card-header">
        <span className="stat-q-type">
          {stat.type === "single_choice"
            ? "单选题"
            : stat.type === "multiple_choice"
              ? "多选题"
              : stat.type === "text_input"
                ? "文本填空"
                : "数字填空"}
        </span>
        <span className="stat-total">{stat.total_answers} 人回答</span>
      </div>
      <h4 className="stat-q-title">{stat.title}</h4>

      {/* 选择题柱状图 */}
      {stat.option_statistics && (
        <OptionStatsWithDropdown options={stat.option_statistics} />
      )}

      {/* 文本回答列表 */}
      {stat.text_responses && (
        <div className="text-responses">
          {stat.text_responses.length === 0 ? (
            <p className="no-data">暂无回答</p>
          ) : (
            stat.text_responses.map((t, i) => (
              <div key={i} className="text-response-item">
                "{t}"
              </div>
            ))
          )}
        </div>
      )}

      {/* 数字统计 */}
      {stat.number_statistics && (
        <div className="number-stats">
          <div className="num-stat-row">
            <div className="num-stat-box">
              <span className="num-stat-label">平均值</span>
              <span className="num-stat-value">{stat.number_statistics.average}</span>
            </div>
            <div className="num-stat-box">
              <span className="num-stat-label">最小值</span>
              <span className="num-stat-value">{stat.number_statistics.min}</span>
            </div>
            <div className="num-stat-box">
              <span className="num-stat-label">最大值</span>
              <span className="num-stat-value">{stat.number_statistics.max}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function StatisticsView({ surveyId, onBack }: StatisticsViewProps) {
  const [stats, setStats] = useState<SurveyStatistics | null>(null);
  const [responses, setResponses] = useState<ResponseListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"stats" | "responses">("stats");

  useEffect(() => {
    (async () => {
      try {
        const [statsData, responsesData] = await Promise.all([
          getSurveyStatistics(surveyId),
          getResponseList(surveyId),
        ]);
        setStats(statsData);
        setResponses(responsesData);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [surveyId]);

  // 按 respondent_id 分组匿名答卷
  const groupedResponses = (() => {
    const groups: Record<string, ResponseListItem[]> = {};
    for (const r of responses) {
      const key = r.respondent_id || r.response_id;
      if (!groups[key]) groups[key] = [];
      groups[key].push(r);
    }
    return groups;
  })();

  if (loading) {
    return (
      <div className="fill-page">
        <div className="blob blob-orange" />
        <div className="blob blob-blue" />
        <div className="blob blob-yellow" />
        <div className="fill-card">
          <div className="accent-bar" />
          <div className="card-content" style={{ textAlign: "center", padding: "60px 40px" }}>
            <div className="generating-spinner" style={{ margin: "0 auto 24px" }} />
            <p>加载统计中…</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fill-page">
        <div className="blob blob-orange" />
        <div className="blob blob-blue" />
        <div className="blob blob-yellow" />
        <div className="fill-card">
          <div className="accent-bar" />
          <div className="card-content">
            <div className="error-box">
              <span className="error-icon">⚠️</span>
              <span>{error}</span>
            </div>
            <button className="submit-btn" onClick={onBack}>
              ← 返回
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fill-page">
      <div className="blob blob-orange" />
      <div className="blob blob-blue" />
      <div className="blob blob-yellow" />

      <div className="fill-container">
        <div className="fill-card">
          <div className="accent-bar" />
          <div className="card-content">
            <button className="back-link" onClick={onBack}>
              ← 返回
            </button>
            <div className="brand-icon" style={{ background: "linear-gradient(135deg, var(--blue-lighter), var(--blue-light))" }}>
              📊
            </div>
            <div style={{ textAlign: "center" }}>
              <h2 className="fill-title">{stats!.survey_title}</h2>
              <p className="fill-desc">
                共收到 <strong>{stats!.total_responses}</strong> 份答卷
              </p>
            </div>

            {/* 切换 Tab */}
            <div className="stats-tabs">
              <button
                className={`stats-tab ${tab === "stats" ? "active" : ""}`}
                onClick={() => setTab("stats")}
              >
                📊 统计概览
              </button>
              <button
                className={`stats-tab ${tab === "responses" ? "active" : ""}`}
                onClick={() => setTab("responses")}
              >
                📋 答卷列表 ({responses.length})
              </button>
            </div>
          </div>
        </div>

        {/* 统计概览 Tab */}
        {tab === "stats" && stats!.question_statistics.map((qs) => (
          <QuestionStatCard key={qs.question_id} stat={qs} />
        ))}

        {/* 答卷列表 Tab */}
        {tab === "responses" && (
          <div className="fill-card">
            <div className="card-content">
              {responses.length === 0 ? (
                <p className="no-data" style={{ textAlign: "center", padding: 24, color: "var(--brown-light)" }}>暂无答卷</p>
              ) : (
                <div className="response-list">
                  {Object.entries(groupedResponses).map(([userId, userResponses]) => {
                    const first = userResponses[0];
                    const displayName = first.is_anonymous
                      ? `匿名用户 #${userId.slice(-6)}`
                      : first.respondent_name || "未知用户";
                    const hasMultiple = userResponses.length > 1;

                    return (
                      <div key={userId} className="response-group">
                        <div className="response-group-header">
                          <span className="respondent-name">
                            {first.is_anonymous ? "🙈 " : "👤 "}
                            {displayName}
                          </span>
                          {hasMultiple && (
                            <span className="response-count-badge">
                              提交了 {userResponses.length} 次
                            </span>
                          )}
                        </div>
                        {userResponses.map((r, ri) => (
                          <div key={r.response_id} className="response-item">
                            <span className="response-time">
                              {hasMultiple ? `第 ${ri + 1} 次 · ` : ""}
                              {new Date(r.submitted_at).toLocaleString("zh-CN")}
                            </span>
                            {r.completion_time != null && (
                              <span className="response-duration">
                                用时 {Math.floor(r.completion_time / 60)}分{r.completion_time % 60}秒
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="fill-card" style={{ marginTop: 8 }}>
          <div className="card-content">
            <button className="submit-btn" onClick={onBack}>
              ← 返回管理面板
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
