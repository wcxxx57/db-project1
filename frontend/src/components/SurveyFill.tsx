import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import type { PublicSurvey, SurveyQuestionRef, Answer } from "../types";
import { getPublicSurvey, submitResponse, AUTH_TOKEN_KEY, AUTH_USER_KEY } from "../services/api";

interface SurveyFillProps {
  accessCode: string;
  onBack: () => void;
}

/** 解析后的题目（后端返回的 SurveyQuestionRef 已包含完整内容字段） */
type ResolvedQuestion = SurveyQuestionRef & {
  type: string;
  title: string;
  required: boolean;
};

/* ====================================================================
   前端跳转逻辑引擎 —— 与后端 response_service.py 保持一致
   ==================================================================== */

function evaluateCondition(
  condition: any,
  answer: string | string[] | number | undefined,
): boolean {
  if (answer === undefined || answer === null) return false;
  const cType = condition.type;

  if (cType === "select_option") {
    return answer === condition.option_id;
  }

  if (cType === "contains_option") {
    if (!Array.isArray(answer)) return false;
    const targetIds: string[] = condition.option_ids || [];
    if (condition.match_type === "all") {
      return targetIds.every((id: string) => (answer as string[]).includes(id));
    }
    return targetIds.some((id: string) => (answer as string[]).includes(id));
  }

  if (cType === "number_compare") {
    const num = typeof answer === "number" ? answer : parseFloat(String(answer));
    if (isNaN(num)) return false;
    const op = condition.operator;
    const val = condition.value;
    if (op === "eq") return num === val;
    if (op === "ne") return num !== val;
    if (op === "gt") return num > val;
    if (op === "gte") return num >= val;
    if (op === "lt") return num < val;
    if (op === "lte") return num <= val;
    if (op === "between")
      return num >= (condition.min_value ?? -Infinity) && num <= (condition.max_value ?? Infinity);
  }

  return false;
}

function computeJumpTarget(
  question: ResolvedQuestion,
  answer: string | string[] | number | undefined,
): string | null {
  const logic = question.logic;
  if (!logic || !logic.enabled) return null;

  for (const rule of logic.rules) {
    if (evaluateCondition(rule.condition, answer)) {
      if (rule.action.type === "end_survey") return "__END__";
      if (rule.action.type === "jump_to") return rule.action.target_question_id || null;
    }
  }
  return null;
}

/** 根据当前所有答案，计算可见题目序列 */
function computeVisibleQuestions(
  questions: ResolvedQuestion[],
  answersMap: Record<string, string | string[] | number>,
): ResolvedQuestion[] {
  if (questions.length === 0) return [];

  const sorted = [...questions].sort((a, b) => a.order - b.order);
  const qidToIndex: Record<string, number> = {};
  sorted.forEach((q, i) => (qidToIndex[q.question_id] = i));

  const visible: ResolvedQuestion[] = [];
  let idx = 0;

  while (idx < sorted.length) {
    const q = sorted[idx];
    visible.push(q);

    const answer = answersMap[q.question_id];
    const target = computeJumpTarget(q, answer);

    if (target === "__END__") break;
    if (target && target in qidToIndex && qidToIndex[target] > idx) {
      idx = qidToIndex[target];
    } else {
      idx++;
    }
  }

  return visible;
}

/* ====================================================================
   前端答案校验
   ==================================================================== */

function validateAnswer(
  question: ResolvedQuestion,
  answer: string | string[] | number | undefined,
): string | null {
  const v = question.validation || {};

  if (question.required && (answer === undefined || answer === null || answer === "")) {
    return `请回答「${question.title}」`;
  }

  if (answer === undefined || answer === null || answer === "") return null;

  if (question.type === "multiple_choice" && Array.isArray(answer)) {
    if (question.required && answer.length === 0) return `请回答「${question.title}」`;
    const exact = v.exact_selected;
    if (exact !== undefined && exact !== null && answer.length !== exact)
      return `「${question.title}」必须选择 ${exact} 项`;
    if (v.min_selected && answer.length < v.min_selected)
      return `「${question.title}」至少选择 ${v.min_selected} 项`;
    if (v.max_selected && answer.length > v.max_selected)
      return `「${question.title}」最多选择 ${v.max_selected} 项`;
  }

  if (question.type === "text_input" && typeof answer === "string") {
    if (v.min_length && answer.length < v.min_length)
      return `「${question.title}」至少输入 ${v.min_length} 个字`;
    if (v.max_length && answer.length > v.max_length)
      return `「${question.title}」最多输入 ${v.max_length} 个字`;
  }

  if (question.type === "number_input" && typeof answer === "number") {
    if (v.integer_only && !Number.isInteger(answer))
      return `「${question.title}」必须为整数`;
    if (v.min_value !== undefined && v.min_value !== null && answer < v.min_value)
      return `「${question.title}」不能小于 ${v.min_value}`;
    if (v.max_value !== undefined && v.max_value !== null && answer > v.max_value)
      return `「${question.title}」不能大于 ${v.max_value}`;
  }

  return null;
}

function getQuestionTypeLabel(type: string): string {
  if (type === "single_choice") return "单选题";
  if (type === "multiple_choice") return "多选题";
  if (type === "text_input") return "文本填空";
  return "数字填空";
}

/* ====================================================================
   SurveyFill 组件
   ==================================================================== */

export default function SurveyFill({ accessCode, onBack }: SurveyFillProps) {
  const [survey, setSurvey] = useState<PublicSurvey | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string | string[] | number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submissionCount, setSubmissionCount] = useState(0);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [isAnonymousChoice, setIsAnonymousChoice] = useState(false);
  const [topPopup, setTopPopup] = useState<string | null>(null);
  const startTimeRef = useRef(Date.now());

  // 检查登录状态
  const isLoggedIn = !!localStorage.getItem(AUTH_TOKEN_KEY);
  const currentUser = (() => {
    try {
      const raw = localStorage.getItem(AUTH_USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  })();

  // 加载问卷
  useEffect(() => {
    (async () => {
      try {
        const data = await getPublicSurvey(accessCode);
        setSurvey(data);
      } catch (e: any) {
        setError(e.message || "加载失败");
      } finally {
        setLoading(false);
      }
    })();
  }, [accessCode]);

  // 计算可见题目
  const visibleQuestions = useMemo(() => {
    if (!survey) return [];
    return computeVisibleQuestions(survey.questions as ResolvedQuestion[], answers);
  }, [survey, answers]);

  // 当前进度
  const progress = useMemo(() => {
    if (visibleQuestions.length === 0) return 0;
    const answered = visibleQuestions.filter(
      (q) => answers[q.question_id] !== undefined && answers[q.question_id] !== "",
    ).length;
    return Math.round((answered / visibleQuestions.length) * 100);
  }, [visibleQuestions, answers]);

  // 更新答案
  const setAnswer = useCallback(
    (qid: string, value: string | string[] | number) => {
      setAnswers((prev) => ({ ...prev, [qid]: value }));
      setValidationErrors((prev) => {
        const next = { ...prev };
        delete next[qid];
        return next;
      });
    },
    [],
  );

  // 多选切换
  const toggleMultiOption = useCallback(
    (qid: string, optId: string) => {
      setAnswers((prev) => {
        const current = (prev[qid] as string[]) || [];
        const idx = current.indexOf(optId);
        const next = idx >= 0
          ? current.filter((id) => id !== optId)
          : [...current, optId];
        return { ...prev, [qid]: next };
      });
      setValidationErrors((prev) => {
        const next = { ...prev };
        delete next[qid];
        return next;
      });
    },
    [],
  );

  // 提交
  const handleSubmit = useCallback(async () => {
    if (!survey) return;

    const hasSubmitted = Boolean(survey.has_submitted);
    const allowMultiple = Boolean(survey.allow_multiple ?? survey.settings.allow_multiple);
    if (hasSubmitted && !allowMultiple) {
      setTopPopup("您已经提交过该问卷，当前设置为不允许重复提交");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    // 前端校验
    const errors: Record<string, string> = {};
    for (const q of visibleQuestions) {
      const err = validateAnswer(q, answers[q.question_id]);
      if (err) errors[q.question_id] = err;
    }

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      setError("请检查以下题目的回答");
      // 滚动到第一个错误
      const firstErrQid = Object.keys(errors)[0];
      const el = document.getElementById(`q-${firstErrQid}`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const answerList: Answer[] = visibleQuestions
        .filter((q) => answers[q.question_id] !== undefined && answers[q.question_id] !== "")
        .map((q) => ({
          question_id: q.question_id,
          answer: answers[q.question_id],
        }));

      const elapsed = Math.round((Date.now() - startTimeRef.current) / 1000);

      await submitResponse({
        survey_id: survey.survey_id,
        access_code: survey.access_code,
        answers: answerList,
        is_anonymous: isAnonymousChoice,
        completion_time: elapsed,
      }).then((res) => {
        setSubmissionCount((res as any).submission_count || 1);
      });

      setSubmitted(true);
    } catch (e: any) {
      if (e && typeof e.code === "number" && e.code === 3002) {
        setTopPopup("您已经提交过该问卷，不允许重复提交");
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
      setError(e.message || "提交失败");
    } finally {
      setSubmitting(false);
    }
  }, [survey, answers, visibleQuestions]);

  // ============ 渲染 ============

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
            <p>加载问卷中…</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !survey) {
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

  if (!isLoggedIn) {
    return (
      <div className="fill-page">
        <div className="blob blob-orange" />
        <div className="blob blob-blue" />
        <div className="blob blob-yellow" />
        <div className="fill-card">
          <div className="accent-bar" />
          <div className="card-content" style={{ textAlign: "center" }}>
            <div className="brand-icon" style={{ background: "linear-gradient(135deg, var(--orange-lighter), var(--orange-light))" }}>
              🔒
            </div>
            <h2 style={{ color: "var(--brown-deep)", marginTop: 16 }}>需要登录</h2>
            <p style={{ color: "var(--brown-dark)", marginBottom: 24 }}>
              填写问卷需要先登录账号，以便记录您的回答
            </p>
            <button className="submit-btn" onClick={onBack}>
              ← 返回登录
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="fill-page">
        <div className="blob blob-orange" />
        <div className="blob blob-blue" />
        <div className="blob blob-yellow" />
        <div className="fill-card">
          <div className="accent-bar" />
          <div className="card-content" style={{ textAlign: "center" }}>
            <div className="brand-icon" style={{ background: "linear-gradient(135deg, var(--success-bg), #c8e6c9)" }}>
              ✅
            </div>
            <h2 style={{ color: "var(--brown-deep)", marginTop: 16 }}>提交成功</h2>
            <p style={{ color: "var(--brown-dark)" }}>感谢您的参与！</p>
            {submissionCount > 1 && (
              <p style={{ color: "var(--brown-light)", fontSize: 14, marginTop: 8 }}>
                这是您第 {submissionCount} 次提交此问卷
              </p>
            )}
            <button className="submit-btn" style={{ marginTop: 24 }} onClick={onBack}>
              返回首页
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fill-page">
      {topPopup && (
        <div
          style={{
            position: "fixed",
            top: 16,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 9999,
            background: "var(--warn-bg)",
            color: "var(--warn-text)",
            border: "1px solid var(--warn-text)",
            borderRadius: 12,
            boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
            padding: "10px 14px",
            display: "flex",
            alignItems: "center",
            gap: 10,
            maxWidth: "88vw",
          }}
        >
          <span>⚠️</span>
          <span style={{ fontSize: 14 }}>{topPopup}</span>
          <button
            type="button"
            onClick={() => setTopPopup(null)}
            style={{
              marginLeft: 8,
              border: "none",
              background: "transparent",
              color: "var(--warn-text)",
              cursor: "pointer",
              fontSize: 16,
              lineHeight: 1,
            }}
            aria-label="关闭提示"
          >
            ×
          </button>
        </div>
      )}

      <div className="blob blob-orange" />
      <div className="blob blob-blue" />
      <div className="blob blob-yellow" />

      <div className="fill-container">
        {/* 头部信息 */}
        <div className="fill-card">
          <div className="accent-bar" />
          <div className="card-content">
            <button className="back-link" onClick={onBack}>
              ← 返回
            </button>
            <div className="brand-icon">📝</div>
            <div style={{ textAlign: "center" }}>
              <h2 className="fill-title">{survey!.title}</h2>
              {survey!.description && (
                <p className="fill-desc">{survey!.description}</p>
              )}
            </div>

            {/* 进度条 */}
            <div className="quiz-progress-bar">
              <div
                className="quiz-progress-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="progress-text">
              完成进度 {progress}% · 共 {visibleQuestions.length} 题
            </p>

            {survey!.has_submitted && (
              <div
                style={{
                  marginTop: 14,
                  borderRadius: 10,
                  border: "1px solid var(--brown-light)",
                  background: "var(--cream-light)",
                  padding: "10px 12px",
                  color: "var(--brown-dark)",
                  fontSize: 14,
                }}
              >
                {survey!.allow_multiple ?? survey!.settings.allow_multiple
                  ? "您已提交过该问卷，当前允许重复提交。"
                  : "您已提交过该问卷，当前不允许重复提交。"}
              </div>
            )}
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="error-box" style={{ margin: "16px 0" }}>
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* 题目列表 */}
        {visibleQuestions.map((q, qi) => {
          const answer = answers[q.question_id];
          const vErr = validationErrors[q.question_id];

          return (
            <div
              key={q.question_id}
              id={`q-${q.question_id}`}
              className={`fill-card question-fill-card ${vErr ? "has-error" : ""}`}
            >
              <div className="card-content">
                {/* 题目标题 */}
                <div className="fill-q-header">
                  <span className="fill-q-number">Q{q.order}</span>
                  <span className="fill-q-title">
                    {q.title}
                    {q.required && <span className="fill-required">*</span>}
                  </span>
                  <span
                    style={{
                      marginLeft: "auto",
                      fontSize: 12,
                      color: "var(--brown-medium)",
                      background: "var(--cream-light)",
                      border: "1px solid var(--brown-light)",
                      borderRadius: 999,
                      padding: "2px 10px",
                    }}
                  >
                    {getQuestionTypeLabel(q.type)}
                  </span>
                </div>

                {/* 单选题 */}
                {q.type === "single_choice" && (
                  <div className="quiz-options">
                    {(q.options || []).map((opt, oi) => (
                      <button
                        key={opt.option_id}
                        type="button"
                        className={`quiz-option ${answer === opt.option_id ? "selected" : ""}`}
                        onClick={() => setAnswer(q.question_id, opt.option_id)}
                      >
                        <span className="option-label">
                          {String.fromCharCode(65 + oi)}
                        </span>
                        <span className="option-text">{opt.text}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* 多选题 */}
                {q.type === "multiple_choice" && (
                  <div className="quiz-options">
                    {(q.options || []).map((opt, oi) => {
                      const selected = Array.isArray(answer) && (answer as string[]).includes(opt.option_id);
                      return (
                        <button
                          key={opt.option_id}
                          type="button"
                          className={`quiz-option ${selected ? "selected" : ""}`}
                          onClick={() => toggleMultiOption(q.question_id, opt.option_id)}
                        >
                          <span className="option-label">
                            {selected ? "✓" : String.fromCharCode(65 + oi)}
                          </span>
                          <span className="option-text">{opt.text}</span>
                        </button>
                      );
                    })}
                    {q.validation && (
                      <p className="fill-hint">
                        {q.validation.exact_selected
                          ? `请选择 ${q.validation.exact_selected} 项`
                          : [
                              q.validation.min_selected ? `至少 ${q.validation.min_selected} 项` : "",
                              q.validation.max_selected ? `最多 ${q.validation.max_selected} 项` : "",
                            ]
                              .filter(Boolean)
                              .join("，")}
                      </p>
                    )}
                  </div>
                )}

                {/* 文本填空 */}
                {q.type === "text_input" && (
                  <div>
                    <textarea
                      className="fill-textarea"
                      placeholder="请输入您的回答"
                      value={(answer as string) || ""}
                      onChange={(e) => setAnswer(q.question_id, e.target.value)}
                    />
                    {q.validation && (
                      <p className="fill-hint">
                        {[
                          q.validation.min_length ? `至少 ${q.validation.min_length} 字` : "",
                          q.validation.max_length ? `最多 ${q.validation.max_length} 字` : "",
                        ]
                          .filter(Boolean)
                          .join("，")}
                        {q.validation.max_length && typeof answer === "string" && (
                          <span>
                            {" "}
                            · 已输入 {(answer as string).length}/{q.validation.max_length}
                          </span>
                        )}
                      </p>
                    )}
                  </div>
                )}

                {/* 数字填空 */}
                {q.type === "number_input" && (
                  <div>
                    <input
                      type="number"
                      className="fill-number-input"
                      placeholder="请输入数字"
                      value={answer !== undefined ? String(answer) : ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === "") {
                          setAnswers((prev) => {
                            const next = { ...prev };
                            delete next[q.question_id];
                            return next;
                          });
                          return;
                        }
                        const num = q.validation?.integer_only
                          ? parseInt(val, 10)
                          : parseFloat(val);
                        if (!isNaN(num)) setAnswer(q.question_id, num);
                      }}
                    />
                    {q.validation && (
                      <p className="fill-hint">
                        {[
                          q.validation.integer_only ? "必须为整数" : "",
                          q.validation.min_value !== undefined && q.validation.min_value !== null
                            ? `最小值 ${q.validation.min_value}`
                            : "",
                          q.validation.max_value !== undefined && q.validation.max_value !== null
                            ? `最大值 ${q.validation.max_value}`
                            : "",
                        ]
                          .filter(Boolean)
                          .join("，")}
                      </p>
                    )}
                  </div>
                )}

                {/* 校验错误 */}
                {vErr && (
                  <div className="field-error">{vErr}</div>
                )}
              </div>
            </div>
          );
        })}

        {/* 提交按钮 */}
        <div className="fill-card" style={{ marginTop: 8 }}>
          <div className="card-content">
            {/* 匿名选项 & 提交者信息 */}
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: "14px", color: "var(--brown-dark)", marginBottom: 8 }}>
                当前用户：<strong>{currentUser?.username || "未知"}</strong>
              </p>
              {survey!.settings.allow_anonymous && (
                <label
                  className="checkbox-label"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "15px",
                    color: "var(--brown-dark)",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isAnonymousChoice}
                    onChange={(e) => setIsAnonymousChoice(e.target.checked)}
                  />
                  匿名提交（结果页不显示我的身份）
                </label>
              )}
            </div>
            <button
              className="submit-btn"
              disabled={submitting}
              onClick={handleSubmit}
            >
              {submitting ? "提交中..." : "🚀 提交问卷"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
