import { useCallback, useEffect, useState } from "react";
import type { Question, QuestionOption, QuestionLogic, LogicRule, Survey } from "../types";
import { getSurveyDetail, updateSurvey } from "../services/api";

interface SurveyEditorProps {
  surveyId: string;
  onBack: () => void;
}

const QUESTION_TYPES = [
  { value: "single_choice", label: "单选题" },
  { value: "multiple_choice", label: "多选题" },
  { value: "text_input", label: "文本填空" },
  { value: "number_input", label: "数字填空" },
];

function makeId(prefix: string, index: number) {
  return `${prefix}${index + 1}`;
}

function formatDateTimeLocal(isoString?: string): string {
  if (!isoString) return "";
  // 直接截取前 16 位 (YYYY-MM-DDTHH:MM)，不做时区转换
  // 这样可以保持用户输入的本地时间
  return isoString.substring(0, 16);
}

function toIsoFromLocalDateTime(localDateTime?: string): string | undefined {
  if (!localDateTime) return undefined;
  // 不做时区转换，直接补充秒数返回
  // 保持用户输入的本地时间（问卷截止时间通常是本地时间概念）
  return localDateTime + ":00";
}

export default function SurveyEditor({ surveyId, onBack }: SurveyEditorProps) {
  const [survey, setSurvey] = useState<Survey | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [allowAnonymous, setAllowAnonymous] = useState(true);
  const [allowMultiple, setAllowMultiple] = useState(false);
  const [deadline, setDeadline] = useState("");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [expandedQ, setExpandedQ] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // 验证题目的 validation 规则
  const validateQuestion = useCallback((q: Question): string | null => {
    if (!q.validation) return null;
    
    const v = q.validation;
    
    // 多选题验证
    if (q.type === "multiple_choice") {
      if (v.min_selected !== undefined && v.max_selected !== undefined && v.max_selected < v.min_selected) {
        return `「${q.title}」最多选择项(${v.max_selected})不能小于最少选择项(${v.min_selected})`;
      }
    }
    
    // 文本填空验证
    if (q.type === "text_input") {
      if (v.min_length !== undefined && v.max_length !== undefined && v.max_length < v.min_length) {
        return `「${q.title}」最多字数(${v.max_length})不能小于最少字数(${v.min_length})`;
      }
    }
    
    // 数字填空验证
    if (q.type === "number_input") {
      if (v.min_value !== undefined && v.max_value !== undefined && v.max_value < v.min_value) {
        return `「${q.title}」最大值(${v.max_value})不能小于最小值(${v.min_value})`;
      }
    }
    
    return null;
  }, []);

  // 验证所有题目
  const validateAllQuestions = useCallback(() => {
    const errors: Record<string, string> = {};
    questions.forEach((q) => {
      const error = validateQuestion(q);
      if (error) {
        errors[q.question_id] = error;
      }
    });
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [questions, validateQuestion]);

  // 加载问卷
  useEffect(() => {
    (async () => {
      try {
        const data = await getSurveyDetail(surveyId);
        setSurvey(data);
        setTitle(data.title);
        setDescription(data.description || "");
        setAllowAnonymous(data.settings.allow_anonymous);
        setAllowMultiple(data.settings.allow_multiple);
        setDeadline(formatDateTimeLocal(data.deadline));
        setQuestions(data.questions || []);
      } catch (e: any) {
        setMessage(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [surveyId]);

  // 保存
  const handleSave = useCallback(async () => {
    // 先验证
    if (!validateAllQuestions()) {
      setMessage("❌ 保存失败：存在验证错误，请检查题目设置");
      return;
    }
    
    setSaving(true);
    setMessage(null);
    try {
      await updateSurvey(surveyId, {
        title,
        description: description || undefined,
        settings: { allow_anonymous: allowAnonymous, allow_multiple: allowMultiple },
        deadline: toIsoFromLocalDateTime(deadline),
        questions,
      });
      setMessage("✅ 保存成功");
    } catch (e: any) {
      setMessage(e.message);
    } finally {
      setSaving(false);
    }
  }, [surveyId, title, description, allowAnonymous, allowMultiple, deadline, questions, validateAllQuestions]);

  // 添加题目
  const addQuestion = useCallback(
    (type: string) => {
      const order = questions.length + 1;
      const qid = `q${order}`;
      const newQ: Question = {
        question_id: qid,
        type: type as Question["type"],
        title: "",
        required: true,
        order,
        options:
          type === "single_choice" || type === "multiple_choice"
            ? [
                { option_id: "opt1", text: "选项1" },
                { option_id: "opt2", text: "选项2" },
              ]
            : [],
        validation: {},
        logic: { enabled: false, rules: [] },
      };
      setQuestions((prev) => [...prev, newQ]);
      setExpandedQ(qid);
    },
    [questions],
  );

  // 删除题目
  const removeQuestion = useCallback((qid: string) => {
    setQuestions((prev) => {
      const filtered = prev.filter((q) => q.question_id !== qid);
      return filtered.map((q, i) => ({ ...q, order: i + 1 }));
    });
  }, []);

  // 上移题目
  const moveQuestionUp = useCallback((index: number) => {
    if (index <= 0) return;
    setQuestions((prev) => {
      const next = [...prev];
      [next[index - 1], next[index]] = [next[index], next[index - 1]];
      return next.map((q, i) => ({ ...q, order: i + 1 }));
    });
  }, []);

  // 下移题目
  const moveQuestionDown = useCallback((index: number) => {
    setQuestions((prev) => {
      if (index >= prev.length - 1) return prev;
      const next = [...prev];
      [next[index], next[index + 1]] = [next[index + 1], next[index]];
      return next.map((q, i) => ({ ...q, order: i + 1 }));
    });
  }, []);

  // 更新题目字段
  const updateQuestion = useCallback(
    (qid: string, patch: Partial<Question>) => {
      setQuestions((prev) =>
        prev.map((q) => (q.question_id === qid ? { ...q, ...patch } : q)),
      );
      // 实时验证
      setTimeout(() => {
        const updatedQ = questions.find(q => q.question_id === qid);
        if (updatedQ) {
          const merged = { ...updatedQ, ...patch };
          const error = validateQuestion(merged);
          setValidationErrors(prev => {
            const next = { ...prev };
            if (error) {
              next[qid] = error;
            } else {
              delete next[qid];
            }
            return next;
          });
        }
      }, 0);
    },
    [questions, validateQuestion],
  );

  // 选项操作
  const addOption = useCallback(
    (qid: string) => {
      setQuestions((prev) =>
        prev.map((q) => {
          if (q.question_id !== qid) return q;
          const opts = q.options || [];
          const uniqueSuffix = `${Date.now().toString(36)}_${Math.random()
            .toString(36)
            .slice(2, 8)}`;
          const newOpt: QuestionOption = {
            option_id: `opt_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 6)}`,
            text: `选项${opts.length + 1}`,
          };
          return { ...q, options: [...opts, newOpt] };
        }),
      );
    },
    [],
  );

  const removeOption = useCallback((qid: string, optId: string) => {
    setQuestions((prev) =>
      prev.map((q) => {
        if (q.question_id !== qid) return q;
        return {
          ...q,
          options: (q.options || []).filter((o) => o.option_id !== optId),
        };
      }),
    );
  }, []);

  const updateOptionText = useCallback(
    (qid: string, optId: string, text: string) => {
      setQuestions((prev) =>
        prev.map((q) => {
          if (q.question_id !== qid) return q;
          return {
            ...q,
            options: (q.options || []).map((o) =>
              o.option_id === optId ? { ...o, text } : o,
            ),
          };
        }),
      );
    },
    [],
  );

  // 跳转逻辑操作
  const toggleLogic = useCallback((qid: string) => {
    setQuestions((prev) =>
      prev.map((q) => {
        if (q.question_id !== qid) return q;
        const logic = q.logic || { enabled: false, rules: [] };
        return { ...q, logic: { ...logic, enabled: !logic.enabled } };
      }),
    );
  }, []);

  const addLogicRule = useCallback(
    (qid: string) => {
      setQuestions((prev) =>
        prev.map((q) => {
          if (q.question_id !== qid) return q;
          const logic = q.logic || { enabled: true, rules: [] };
          const qType = q.type;

          let newRule: LogicRule;
          if (qType === "single_choice") {
            newRule = {
              condition: { type: "select_option", option_id: (q.options || [])[0]?.option_id || "" },
              action: { type: "jump_to", target_question_id: "" },
            };
          } else if (qType === "multiple_choice") {
            newRule = {
              condition: { type: "contains_option", option_ids: [], match_type: "any" },
              action: { type: "jump_to", target_question_id: "" },
            };
          } else {
            newRule = {
              condition: { type: "number_compare", operator: "eq", value: 0 },
              action: { type: "jump_to", target_question_id: "" },
            };
          }
          return { ...q, logic: { ...logic, enabled: true, rules: [...logic.rules, newRule] } };
        }),
      );
    },
    [],
  );

  const removeLogicRule = useCallback((qid: string, ruleIndex: number) => {
    setQuestions((prev) =>
      prev.map((q) => {
        if (q.question_id !== qid) return q;
        const logic = q.logic || { enabled: false, rules: [] };
        const rules = [...logic.rules];
        rules.splice(ruleIndex, 1);
        return { ...q, logic: { ...logic, rules } };
      }),
    );
  }, []);

  const updateLogicRule = useCallback(
    (qid: string, ruleIndex: number, patch: Partial<LogicRule>) => {
      setQuestions((prev) =>
        prev.map((q) => {
          if (q.question_id !== qid) return q;
          const logic = q.logic || { enabled: false, rules: [] };
          const rules = logic.rules.map((r, i) =>
            i === ruleIndex ? { ...r, ...patch } : r,
          );
          return { ...q, logic: { ...logic, rules } };
        }),
      );
    },
    [],
  );

  if (loading) {
    return (
      <div className="editor-page">
        <div className="blob blob-orange" />
        <div className="blob blob-blue" />
        <div className="blob blob-yellow" />
        <div className="editor-container"><p>加载中…</p></div>
      </div>
    );
  }

  return (
    <div className="editor-page">
      <div className="blob blob-orange" />
      <div className="blob blob-blue" />
      <div className="blob blob-yellow" />

      <div className="editor-container">
        {/* Top bar */}
        <div className="editor-topbar">
          <button className="back-btn" onClick={onBack}>
            ← 返回
          </button>
          <h2 className="editor-title-label">编辑问卷</h2>
          <button
            className="save-btn"
            disabled={saving}
            onClick={handleSave}
          >
            {saving ? "保存中..." : "💾 保存"}
          </button>
        </div>

        {message && (
          <div
            className="error-box"
            style={{
              background: message.includes("✅") ? "var(--success-bg)" : "var(--warn-bg)",
              color: message.includes("✅") ? "var(--success-text)" : "var(--warn-text)",
              borderLeftColor: message.includes("✅") ? "var(--success-text)" : "var(--warn-text)",
            }}
          >
            <span>{message}</span>
          </div>
        )}

        {/* 警告横幅 - 当问卷已有答卷数据时显示 */}
        {survey && survey.response_count > 0 && (
          <div
            className="error-box"
            style={{
              background: "#fef2f2",
              color: "#991b1b",
              borderLeftColor: "#dc2626",
              borderLeftWidth: "4px",
              marginBottom: "1.5rem",
            }}
          >
            <div style={{ fontWeight: "600", marginBottom: "0.5rem" }}>
              ⚠️ 注意：该问卷已有 {survey.response_count} 份答卷数据
            </div>
            <div style={{ fontSize: "0.9rem", lineHeight: "1.6" }}>
              <p style={{ marginBottom: "0.5rem" }}>修改题目结构（删除题目、修改选项等）可能导致：</p>
              <ul style={{ marginLeft: "1.5rem", marginBottom: "0.75rem" }}>
                <li>历史答卷数据无法正确统计</li>
                <li>统计结果出现数据缺失或警告信息</li>
              </ul>
              <p style={{ fontWeight: "600", marginBottom: "0.5rem" }}>建议：</p>
              <ul style={{ marginLeft: "1.5rem" }}>
                <li>如只是修正错别字或调整说明，可以继续编辑</li>
                <li>如需大幅修改题目结构，请创建新问卷</li>
              </ul>
            </div>
          </div>
        )}

        {/* 问卷基本信息 */}
        <div className="editor-section">
          <h3 className="section-title">基本信息</h3>
          <div className="field-row">
            <label className="field-label">问卷标题</label>
            <input
              className="editor-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="请输入问卷标题"
            />
          </div>
          <div className="field-row">
            <label className="field-label">问卷说明</label>
            <textarea
              className="editor-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="请输入问卷说明（可选）"
            />
          </div>
          <div className="field-row-inline">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={allowAnonymous}
                onChange={(e) => setAllowAnonymous(e.target.checked)}
              />
              允许匿名填写
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={allowMultiple}
                onChange={(e) => setAllowMultiple(e.target.checked)}
              />
              允许多次提交
            </label>
          </div>
          <div className="field-row">
            <label className="field-label">截止时间</label>
            <input
              type="datetime-local"
              className="editor-input"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
            />
          </div>
        </div>

        {/* 题目列表 */}
        <div className="editor-section">
          <h3 className="section-title">
            题目列表（{questions.length} 题）
          </h3>

          {questions.map((q, qi) => {
            const isExpanded = expandedQ === q.question_id;
            const typeLabel = QUESTION_TYPES.find((t) => t.value === q.type)?.label || q.type;

            return (
              <div key={q.question_id} className="question-card">
                {/* 题目头部 */}
                <div
                  className="question-header"
                  onClick={() => setExpandedQ(isExpanded ? null : q.question_id)}
                >
                  <span className="q-order">Q{qi + 1}</span>
                  <span className="q-type-badge">{typeLabel}</span>
                  <span className="q-title-preview">
                    {q.title || "(未填写题目)"}
                  </span>
                  {q.required && <span className="q-required-badge">必答</span>}
                  {q.logic?.enabled && (
                    <span className="q-logic-badge">⚡跳转</span>
                  )}
                  <span className="q-move-btns" onClick={(e) => e.stopPropagation()}>
                    <button
                      className="q-move-btn"
                      disabled={qi === 0}
                      onClick={() => moveQuestionUp(qi)}
                      title="上移"
                    >
                      ▲
                    </button>
                    <button
                      className="q-move-btn"
                      disabled={qi === questions.length - 1}
                      onClick={() => moveQuestionDown(qi)}
                      title="下移"
                    >
                      ▼
                    </button>
                  </span>
                  <span className="q-expand-icon">{isExpanded ? "▼" : "▶"}</span>
                </div>

                {/* 展开详情 */}
                {isExpanded && (
                  <div className="question-body">
                    <div className="field-row">
                      <label className="field-label">题目文本</label>
                      <input
                        className="editor-input"
                        value={q.title}
                        onChange={(e) => updateQuestion(q.question_id, { title: e.target.value })}
                        placeholder="请输入题目"
                      />
                    </div>

                    <div className="field-row-inline">
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={q.required}
                          onChange={(e) => updateQuestion(q.question_id, { required: e.target.checked })}
                        />
                        必答题
                      </label>
                    </div>

                    {/* 选项编辑（选择题） */}
                    {(q.type === "single_choice" || q.type === "multiple_choice") && (
                      <div className="options-section">
                        <label className="field-label">选项</label>
                        {(q.options || []).map((opt) => (
                          <div key={opt.option_id} className="option-row">
                            <input
                              className="option-input"
                              value={opt.text}
                              onChange={(e) =>
                                updateOptionText(q.question_id, opt.option_id, e.target.value)
                              }
                            />
                            <button
                              className="remove-opt-btn"
                              onClick={() => removeOption(q.question_id, opt.option_id)}
                            >
                              ✕
                            </button>
                          </div>
                        ))}
                        <button
                          className="add-opt-btn"
                          onClick={() => addOption(q.question_id)}
                        >
                          ＋ 添加选项
                        </button>
                      </div>
                    )}

                    {/* 校验规则 */}
                    {q.type === "multiple_choice" && (
                      <div className="validation-section">
                        <label className="field-label">选择数量限制</label>
                        <div className="field-row-inline">
                          <label>
                            最少
                            <input
                              type="number"
                              className="small-input"
                              value={q.validation?.min_selected ?? ""}
                              onChange={(e) =>
                                updateQuestion(q.question_id, {
                                  validation: {
                                    ...q.validation,
                                    min_selected: e.target.value ? Number(e.target.value) : undefined,
                                  },
                                })
                              }
                            />
                          </label>
                          <label>
                            最多
                            <input
                              type="number"
                              className="small-input"
                              value={q.validation?.max_selected ?? ""}
                              onChange={(e) =>
                                updateQuestion(q.question_id, {
                                  validation: {
                                    ...q.validation,
                                    max_selected: e.target.value ? Number(e.target.value) : undefined,
                                  },
                                })
                              }
                            />
                          </label>
                          <label>
                            精确
                            <input
                              type="number"
                              className="small-input"
                              value={q.validation?.exact_selected ?? ""}
                              onChange={(e) =>
                                updateQuestion(q.question_id, {
                                  validation: {
                                    ...q.validation,
                                    exact_selected: e.target.value ? Number(e.target.value) : undefined,
                                  },
                                })
                              }
                            />
                          </label>
                        </div>
                        {validationErrors[q.question_id] && (
                          <div style={{ color: "#dc2626", fontSize: "0.875rem", marginTop: "0.5rem" }}>
                            ⚠️ {validationErrors[q.question_id]}
                          </div>
                        )}
                      </div>
                    )}

                    {q.type === "text_input" && (
                      <div className="validation-section">
                        <label className="field-label">字数限制</label>
                        <div className="field-row-inline">
                          <label>最少 <input type="number" className="small-input" value={q.validation?.min_length ?? ""} onChange={(e) => updateQuestion(q.question_id, { validation: { ...q.validation, min_length: e.target.value ? Number(e.target.value) : undefined } })} /></label>
                          <label>最多 <input type="number" className="small-input" value={q.validation?.max_length ?? ""} onChange={(e) => updateQuestion(q.question_id, { validation: { ...q.validation, max_length: e.target.value ? Number(e.target.value) : undefined } })} /></label>
                        </div>
                        {validationErrors[q.question_id] && (
                          <div style={{ color: "#dc2626", fontSize: "0.875rem", marginTop: "0.5rem" }}>
                            ⚠️ {validationErrors[q.question_id]}
                          </div>
                        )}
                      </div>
                    )}

                    {q.type === "number_input" && (
                      <div className="validation-section">
                        <label className="field-label">数值限制</label>
                        <div className="field-row-inline">
                          <label>最小值 <input type="number" className="small-input" value={q.validation?.min_value ?? ""} onChange={(e) => updateQuestion(q.question_id, { validation: { ...q.validation, min_value: e.target.value ? Number(e.target.value) : undefined } })} /></label>
                          <label>最大值 <input type="number" className="small-input" value={q.validation?.max_value ?? ""} onChange={(e) => updateQuestion(q.question_id, { validation: { ...q.validation, max_value: e.target.value ? Number(e.target.value) : undefined } })} /></label>
                          <label className="checkbox-label">
                            <input type="checkbox" checked={q.validation?.integer_only ?? false} onChange={(e) => updateQuestion(q.question_id, { validation: { ...q.validation, integer_only: e.target.checked } })} />
                            必须整数
                          </label>
                        </div>
                        {validationErrors[q.question_id] && (
                          <div style={{ color: "#dc2626", fontSize: "0.875rem", marginTop: "0.5rem" }}>
                            ⚠️ {validationErrors[q.question_id]}
                          </div>
                        )}
                      </div>
                    )}

                    {/* 跳转逻辑配置 */}
                    {(q.type === "single_choice" || q.type === "multiple_choice" || q.type === "number_input") && (
                      <div className="logic-section">
                        <div className="logic-header">
                          <label className="checkbox-label">
                            <input
                              type="checkbox"
                              checked={q.logic?.enabled ?? false}
                              onChange={() => toggleLogic(q.question_id)}
                            />
                            <span className="field-label">⚡ 跳转逻辑</span>
                          </label>
                          {q.logic?.enabled && (
                            <button
                              className="add-opt-btn"
                              onClick={() => addLogicRule(q.question_id)}
                            >
                              ＋ 添加规则
                            </button>
                          )}
                        </div>

                        {q.logic?.enabled &&
                          (q.logic.rules || []).map((rule, ri) => (
                            <div key={ri} className="logic-rule-card">
                              <div className="logic-rule-header">
                                <span>规则 {ri + 1}</span>
                                <button
                                  className="remove-opt-btn"
                                  onClick={() => removeLogicRule(q.question_id, ri)}
                                >
                                  ✕
                                </button>
                              </div>

                              {/* 条件 */}
                              {q.type === "single_choice" && (
                                <div className="logic-condition">
                                  <span>当选择</span>
                                  <select
                                    className="logic-select"
                                    value={rule.condition.option_id || ""}
                                    onChange={(e) =>
                                      updateLogicRule(q.question_id, ri, {
                                        condition: { type: "select_option", option_id: e.target.value },
                                      })
                                    }
                                  >
                                    <option value="">选择选项</option>
                                    {(q.options || []).map((o) => (
                                      <option key={o.option_id} value={o.option_id}>
                                        {o.text}
                                      </option>
                                    ))}
                                  </select>
                                  <span>时</span>
                                </div>
                              )}

                              {q.type === "multiple_choice" && (
                                <div className="logic-condition">
                                  <span>当选项包含</span>
                                  <select
                                    className="logic-select"
                                    value={rule.condition.match_type || "any"}
                                    onChange={(e) =>
                                      updateLogicRule(q.question_id, ri, {
                                        condition: { ...rule.condition, type: "contains_option", match_type: e.target.value as "any" | "all" },
                                      })
                                    }
                                  >
                                    <option value="any">任一(OR)</option>
                                    <option value="all">全部(AND)</option>
                                  </select>
                                  <div className="logic-multi-opts">
                                    {(q.options || []).map((o) => {
                                      const selected = (rule.condition.option_ids || []).includes(o.option_id);
                                      return (
                                        <label key={o.option_id} className="checkbox-label small">
                                          <input
                                            type="checkbox"
                                            checked={selected}
                                            onChange={(e) => {
                                              const ids = [...(rule.condition.option_ids || [])];
                                              if (e.target.checked) ids.push(o.option_id);
                                              else {
                                                const idx = ids.indexOf(o.option_id);
                                                if (idx >= 0) ids.splice(idx, 1);
                                              }
                                              updateLogicRule(q.question_id, ri, {
                                                condition: { ...rule.condition, type: "contains_option", option_ids: ids },
                                              });
                                            }}
                                          />
                                          {o.text}
                                        </label>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {q.type === "number_input" && (
                                <div className="logic-condition">
                                  <span>当数值</span>
                                  <select
                                    className="logic-select"
                                    value={rule.condition.operator || "eq"}
                                    onChange={(e) =>
                                      updateLogicRule(q.question_id, ri, {
                                        condition: { ...rule.condition, type: "number_compare", operator: e.target.value as any },
                                      })
                                    }
                                  >
                                    <option value="eq">等于</option>
                                    <option value="ne">不等于</option>
                                    <option value="gt">大于</option>
                                    <option value="gte">大于等于</option>
                                    <option value="lt">小于</option>
                                    <option value="lte">小于等于</option>
                                    <option value="between">介于</option>
                                  </select>
                                  {rule.condition.operator === "between" ? (
                                    <>
                                      <input type="number" className="small-input" value={rule.condition.min_value ?? ""} onChange={(e) => updateLogicRule(q.question_id, ri, { condition: { ...rule.condition, min_value: Number(e.target.value) } })} />
                                      <span>至</span>
                                      <input type="number" className="small-input" value={rule.condition.max_value ?? ""} onChange={(e) => updateLogicRule(q.question_id, ri, { condition: { ...rule.condition, max_value: Number(e.target.value) } })} />
                                    </>
                                  ) : (
                                    <input type="number" className="small-input" value={rule.condition.value ?? ""} onChange={(e) => updateLogicRule(q.question_id, ri, { condition: { ...rule.condition, value: Number(e.target.value) } })} />
                                  )}
                                </div>
                              )}

                              {/* 动作 */}
                              <div className="logic-action">
                                <span>则</span>
                                <select
                                  className="logic-select"
                                  value={rule.action.type}
                                  onChange={(e) =>
                                    updateLogicRule(q.question_id, ri, {
                                      action: { ...rule.action, type: e.target.value as "jump_to" | "end_survey" },
                                    })
                                  }
                                >
                                  <option value="jump_to">跳转到</option>
                                  <option value="end_survey">结束问卷</option>
                                </select>
                                {rule.action.type === "jump_to" && (
                                  <select
                                    className="logic-select"
                                    value={rule.action.target_question_id || ""}
                                    onChange={(e) =>
                                      updateLogicRule(q.question_id, ri, {
                                        action: { ...rule.action, target_question_id: e.target.value },
                                      })
                                    }
                                  >
                                    <option value="">选择目标题目</option>
                                    {questions
                                      .filter((tq) => tq.question_id !== q.question_id)
                                      .map((tq, ti) => (
                                        <option key={tq.question_id} value={tq.question_id}>
                                          Q{questions.indexOf(tq) + 1} - {tq.title || "(未命名)"}
                                        </option>
                                      ))}
                                  </select>
                                )}
                              </div>
                            </div>
                          ))}
                      </div>
                    )}

                    <button
                      className="remove-q-btn"
                      onClick={() => removeQuestion(q.question_id)}
                    >
                      🗑 删除此题
                    </button>
                  </div>
                )}
              </div>
            );
          })}

          {/* 添加题目按钮 */}
          <div className="add-question-bar">
            {QUESTION_TYPES.map((t) => (
              <button
                key={t.value}
                className="add-q-btn"
                onClick={() => addQuestion(t.value)}
              >
                ＋ {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
