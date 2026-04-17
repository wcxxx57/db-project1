import { useCallback, useEffect, useState } from "react";
import type {
  QuestionListItem,
  QuestionDetail,
  QuestionUsageItem,
  QuestionOption,
  QuestionVersion,
  CrossSurveyQuestionStatistics,
} from "../types";
import {
  getMyQuestions,
  getSharedQuestions,
  getBankedQuestions,
  getQuestionDetail,
  createQuestion,
  createNewVersion,
  updateVersion,
  shareQuestion,
  unshareQuestion,
  getQuestionUsage,
  deleteQuestion,
  getCrossSurveyStats,
  addToBank,
  removeFromBank,
} from "../services/api";

interface QuestionManagerProps {
  onBack: () => void;
}

const TYPE_LABEL: Record<string, string> = {
  single_choice: "单选题",
  multiple_choice: "多选题",
  text_input: "文本填空",
  number_input: "数字填空",
};

type TabType = "my" | "shared" | "bank";

// ===== 小组件 =====

function ValidationSummary({ v }: { v: QuestionVersion }) {
  const val = v.validation;
  if (!val || Object.keys(val).length === 0) return null;
  const parts: string[] = [];
  if (val.min_selected != null) parts.push(`最少选 ${val.min_selected}`);
  if (val.max_selected != null) parts.push(`最多选 ${val.max_selected}`);
  if (val.exact_selected != null) parts.push(`必须选 ${val.exact_selected}`);
  if (val.min_length != null) parts.push(`最少 ${val.min_length} 字`);
  if (val.max_length != null) parts.push(`最多 ${val.max_length} 字`);
  if (val.min_value != null) parts.push(`最小值 ${val.min_value}`);
  if (val.max_value != null) parts.push(`最大值 ${val.max_value}`);
  if (val.integer_only) parts.push("仅整数");
  if (parts.length === 0) return null;
  return (
    <span style={{ fontSize: "0.75rem", color: "#999" }}>
      ({parts.join("，")})
    </span>
  );
}

function OptionList({ v }: { v: QuestionVersion }) {
  if (!v.options || v.options.length === 0) return null;
  const icon = v.type === "single_choice" ? "○" : "☐";
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "0.35rem 1rem",
        marginTop: "0.3rem",
      }}
    >
      {v.options.map((opt) => (
        <span
          key={opt.option_id}
          style={{ fontSize: "0.85rem", color: "#555" }}
        >
          {icon} {opt.text}
        </span>
      ))}
    </div>
  );
}

function VersionCard({ v }: { v: QuestionVersion }) {
  return (
    <div
      style={{
        padding: "0.65rem 0.85rem",
        background: "#faf8f3",
        borderRadius: "0.4rem",
        marginBottom: "0.5rem",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontWeight: 700,
            fontSize: "0.85rem",
            color: "var(--brown-dark)",
          }}
        >
          v{v.version_number}
        </span>
        <span className="q-type-badge" style={{ fontSize: "0.7rem" }}>
          {TYPE_LABEL[v.type] || v.type}
        </span>
        <span style={{ fontWeight: 500, fontSize: "0.85rem" }}>{v.title}</span>
        {v.parent_version_number !== null && (
          <span style={{ fontSize: "0.72rem", color: "#aaa" }}>
            基于 v{v.parent_version_number}
          </span>
        )}
      </div>
      <OptionList v={v} />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginTop: "0.25rem",
        }}
      >
        <span style={{ fontSize: "0.72rem", color: "#aaa" }}>
          创建者: {v.updated_by || "未知"} |{" "}
          {v.created_at ? new Date(v.created_at).toLocaleString("zh-CN") : ""}
        </span>
        <ValidationSummary v={v} />
      </div>
    </div>
  );
}

// 版本关系图（横向箭头，分支换行）
function VersionTree({ versions }: { versions: QuestionVersion[] }) {
  // 构建 parent → children 映射
  const childrenOf = new Map<number | null, number[]>();
  versions.forEach((v) => {
    const p = v.parent_version_number;
    if (!childrenOf.has(p)) childrenOf.set(p, []);
    childrenOf.get(p)!.push(v.version_number);
  });

  // 收集所有从根到叶的路径
  const paths: number[][] = [];
  function dfs(vn: number, path: number[]) {
    const children = childrenOf.get(vn) || [];
    if (children.length === 0) {
      paths.push(path);
    } else {
      children.forEach((c) => dfs(c, [...path, c]));
    }
  }
  const roots = childrenOf.get(null) || [];
  roots.forEach((r) => dfs(r, [r]));

  // 找出主链（最长路径）用于检测分支起点
  const mainPath = paths.reduce((a, b) => (a.length >= b.length ? a : b), []);
  const mainSet = new Set(mainPath);

  return (
    <div
      style={{
        background: "#faf8f3",
        padding: "0.45rem 0.75rem",
        borderRadius: "0.35rem",
        marginBottom: "0.6rem",
        overflowX: "auto",
      }}
    >
      {/* 主链 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "0.15rem",
        }}
      >
        {mainPath.map((vn, i) => (
          <span
            key={vn}
            style={{ display: "inline-flex", alignItems: "center" }}
          >
            {i > 0 && (
              <span
                style={{
                  color: "#bbb",
                  margin: "0 0.2rem",
                  fontSize: "0.8rem",
                }}
              >
                →
              </span>
            )}
            <span
              style={{
                fontWeight: 700,
                fontSize: "0.8rem",
                color: "var(--brown-dark)",
                background: "#ede5d5",
                borderRadius: "0.25rem",
                padding: "0.1rem 0.35rem",
              }}
            >
              v{vn}
            </span>
          </span>
        ))}
      </div>
      {/* 分支 */}
      {paths
        .filter((p) => p !== mainPath && !p.every((vn) => mainSet.has(vn)))
        .map((path, pi) => {
          // 找到分支起点：path 与 mainPath 的最后一个公共节点
          let branchIdx = 0;
          for (let i = 0; i < path.length && i < mainPath.length; i++) {
            if (path[i] === mainPath[i]) branchIdx = i;
            else break;
          }
          const branchPoint = path[branchIdx];
          const branchNodes = path.slice(branchIdx + 1);
          if (branchNodes.length === 0) return null;
          // 计算缩进：主链中 branchPoint 的位置
          const mainIdx = mainPath.indexOf(branchPoint);
          return (
            <div
              key={pi}
              style={{
                display: "flex",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "0.15rem",
                marginTop: "0.15rem",
              }}
            >
              {/* 缩进占位 */}
              {Array.from({ length: mainIdx }).map((_, si) => (
                <span
                  key={si}
                  style={{ display: "inline-flex", alignItems: "center" }}
                >
                  <span
                    style={{
                      visibility: "hidden",
                      fontWeight: 700,
                      fontSize: "0.8rem",
                      padding: "0.1rem 0.35rem",
                    }}
                  >
                    v{mainPath[si]}
                  </span>
                  <span
                    style={{
                      visibility: "hidden",
                      margin: "0 0.2rem",
                      fontSize: "0.8rem",
                    }}
                  >
                    →
                  </span>
                </span>
              ))}
              {/* 分支箭头 */}
              <span
                style={{
                  color: "#bbb",
                  margin: "0 0.2rem",
                  fontSize: "0.8rem",
                }}
              >
                ↘
              </span>
              {branchNodes.map((vn, i) => (
                <span
                  key={vn}
                  style={{ display: "inline-flex", alignItems: "center" }}
                >
                  {i > 0 && (
                    <span
                      style={{
                        color: "#bbb",
                        margin: "0 0.2rem",
                        fontSize: "0.8rem",
                      }}
                    >
                      →
                    </span>
                  )}
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: "0.8rem",
                      color: "#b45309",
                      background: "#fef3c7",
                      borderRadius: "0.25rem",
                      padding: "0.1rem 0.35rem",
                    }}
                  >
                    v{vn}
                  </span>
                </span>
              ))}
            </div>
          );
        })}
    </div>
  );
}

// ===== 主组件 =====

export default function QuestionManager({ onBack }: QuestionManagerProps) {
  const [tab, setTab] = useState<TabType>("my");
  const [questions, setQuestions] = useState<QuestionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // 展开的题目 ID → 详情
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detailMap, setDetailMap] = useState<
    Record<string, { detail: QuestionDetail; usage: QuestionUsageItem[] }>
  >({});
  const [crossStats, setCrossStats] =
    useState<CrossSurveyQuestionStatistics | null>(null);
  const [showCrossStatsFor, setShowCrossStatsFor] = useState<string | null>(
    null,
  );
  const [bankedRefIds, setBankedRefIds] = useState<Set<string>>(new Set());

  // 新建题目
  const [showCreate, setShowCreate] = useState(false);
  const [newType, setNewType] = useState("single_choice");
  const [newTitle, setNewTitle] = useState("");
  const [newOptions, setNewOptions] = useState<QuestionOption[]>([
    { option_id: "opt1", text: "选项1" },
    { option_id: "opt2", text: "选项2" },
  ]);

  // 共享输入
  const [shareUsername, setShareUsername] = useState("");

  // 编辑模式：修改当前版本 or 创建新版本
  const [editFor, setEditFor] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<"in_place" | "new_version" | null>(
    null,
  );
  const [editChoiceFor, setEditChoiceFor] = useState<string | null>(null); // 显示选择弹窗
  const [versionTitle, setVersionTitle] = useState("");
  const [versionType, setVersionType] = useState("");
  const [versionOptions, setVersionOptions] = useState<QuestionOption[]>([]);

  // ---- 数据 ----

  const loadQuestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data =
        tab === "my"
          ? await getMyQuestions()
          : tab === "bank"
            ? await getBankedQuestions()
            : await getSharedQuestions();
      setQuestions(data);

      try {
        const bankedList = tab === "bank" ? data : await getBankedQuestions();
        setBankedRefIds(
          new Set(bankedList.map((item: QuestionListItem) => item.question_id)),
        );
      } catch {}
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    loadQuestions();
    setExpandedId(null);
    setDetailMap({});
    setCrossStats(null);
  }, [loadQuestions]);

  const loadDetail = useCallback(async (id: string) => {
    try {
      const [d, u] = await Promise.all([
        getQuestionDetail(id),
        getQuestionUsage(id),
      ]);
      setDetailMap((prev) => ({ ...prev, [id]: { detail: d, usage: u } }));
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  const toggleExpand = useCallback(
    (id: string) => {
      if (expandedId === id) {
        setExpandedId(null);
        setCrossStats(null);
        setShowCrossStatsFor(null);
        return;
      }
      setExpandedId(id);
      setCrossStats(null);
      setShowCrossStatsFor(null);
      setEditFor(null);
      setEditMode(null);
      setEditChoiceFor(null);
      if (!detailMap[id]) loadDetail(id);
    },
    [expandedId, detailMap, loadDetail],
  );

  // ---- 操作 ----

  const flash = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(null), 3000);
  };

  const handleAddToBank = useCallback(async (qid: string) => {
    try {
      await addToBank(qid);
      setBankedRefIds((prev) => new Set([...prev, qid]));
      flash("已成功加入我的题库");
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  const handleCreate = useCallback(async () => {
    if (!newTitle.trim()) {
      setError("请输入题目文本");
      return;
    }
    try {
      const result = await createQuestion({
        type: newType,
        title: newTitle,
        options: newType.includes("choice") ? newOptions : undefined,
      });
      // 从题目管理创建的题目自动加入题库
      await addToBank(result.question_id);
      setShowCreate(false);
      setNewTitle("");
      setNewOptions([
        { option_id: "opt1", text: "选项1" },
        { option_id: "opt2", text: "选项2" },
      ]);
      flash("题目创建成功");
      loadQuestions();
    } catch (e: any) {
      setError(e.message);
    }
  }, [newType, newTitle, newOptions, loadQuestions]);

  const handleCreateVersion = useCallback(
    async (qid: string) => {
      const entry = detailMap[qid];
      if (!entry) return;
      try {
        const latest = entry.detail.versions[entry.detail.versions.length - 1];
        await createNewVersion(qid, {
          type: versionType || latest.type,
          title: versionTitle || latest.title,
          options:
            versionType.includes("choice") || latest.type.includes("choice")
              ? versionOptions
              : undefined,
          validation: latest.validation,
          parent_version_number: entry.detail.latest_version_number,
        });
        setEditFor(null);
        setEditMode(null);
        flash("新版本创建成功");
        loadDetail(qid);
        loadQuestions();
      } catch (e: any) {
        setError(e.message);
      }
    },
    [
      detailMap,
      versionTitle,
      versionType,
      versionOptions,
      loadDetail,
      loadQuestions,
    ],
  );

  const handleShare = useCallback(
    async (qid: string) => {
      if (!shareUsername.trim()) return;
      try {
        await shareQuestion(qid, shareUsername.trim());
        setShareUsername("");
        flash("共享成功");
        loadDetail(qid);
      } catch (e: any) {
        setError(e.message);
      }
    },
    [shareUsername, loadDetail],
  );

  const handleUnshare = useCallback(
    async (qid: string, username: string) => {
      try {
        await unshareQuestion(qid, username);
        flash("已取消共享");
        loadDetail(qid);
      } catch (e: any) {
        setError(e.message);
      }
    },
    [loadDetail],
  );

  const handleDelete = useCallback(
    async (qid: string) => {
      if (tab === "bank") {
        if (!window.confirm("确定将该题目移出题库？")) return;
        try {
          await removeFromBank(qid);
          if (expandedId === qid) {
            setExpandedId(null);
          }
          setBankedRefIds((prev) => {
            const next = new Set(prev);
            next.delete(qid);
            return next;
          });
          flash("题目已移出题库");
          loadQuestions();
        } catch (e: any) {
          setError(e.message);
        }
        return;
      }

      // 先获取使用情况
      let usageList: QuestionUsageItem[] = [];
      try {
        usageList = await getQuestionUsage(qid);
      } catch (_) {
        /* 忽略 */
      }

      let confirmMsg = "确定删除该题目？此操作不可恢复。";
      if (usageList.length > 0) {
        const surveyNames = [...new Set(usageList.map((u) => u.survey_title))];
        confirmMsg = `该题目正在被以下 ${surveyNames.length} 份问卷使用：\n\n${surveyNames.map((n) => `  - ${n}`).join("\n")}\n\n删除后将自动从这些问卷中移除该题目。确定删除？`;
      }
      if (!window.confirm(confirmMsg)) return;
      try {
        await deleteQuestion(qid);
        setExpandedId(null);
        flash(
          usageList.length > 0
            ? `题目已删除，已从 ${usageList.length} 份问卷中移除`
            : "题目已删除",
        );
        loadQuestions();
      } catch (e: any) {
        setError(e.message);
      }
    },
    [expandedId, loadQuestions, tab],
  );

  const handleLoadCrossStats = useCallback(
    async (qid: string) => {
      if (showCrossStatsFor === qid) {
        setShowCrossStatsFor(null);
        setCrossStats(null);
        return;
      }
      try {
        setShowCrossStatsFor(qid);
        setCrossStats(await getCrossSurveyStats(qid));
      } catch (e: any) {
        setError(e.message);
        setShowCrossStatsFor(null);
      }
    },
    [showCrossStatsFor],
  );

  // ---- 渲染 ----

  return (
    <div className="editor-page">
      <div className="blob blob-orange" />
      <div className="blob blob-blue" />
      <div className="blob blob-yellow" />

      <div className="editor-container">
        {/* 顶栏 */}
        <div className="editor-topbar">
          <button className="back-btn" onClick={onBack}>
            ← 返回
          </button>
          <h2 className="editor-title-label">题目管理</h2>
          <button
            className="save-btn"
            onClick={() => {
              setShowCreate(true);
              setNewTitle("");
              setNewType("single_choice");
            }}
          >
            ＋ 新建题目
          </button>
        </div>

        {/* 提示 */}
        {(error || message) && (
          <div
            className="error-box"
            style={{
              background: message ? "var(--success-bg)" : "var(--warn-bg)",
              color: message ? "var(--success-text)" : "var(--warn-text)",
              borderLeftColor: message
                ? "var(--success-text)"
                : "var(--warn-text)",
            }}
          >
            <span>{error || message}</span>
            <button
              style={{
                marginLeft: "auto",
                background: "none",
                border: "none",
                cursor: "pointer",
              }}
              onClick={() => {
                setError(null);
                setMessage(null);
              }}
            >
              ✕
            </button>
          </div>
        )}

        {/* 标签页 */}
        <div
          style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem" }}
        >
          {(
            [
              ["my", "我的题目"],
              ["shared", "共享给我"],
              ["bank", "我的题库"],
            ] as [TabType, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              className="add-q-btn"
              style={{
                background:
                  tab === key ? "var(--brown-dark)" : "var(--brown-light)",
                color: tab === key ? "#fff" : "var(--brown-dark)",
                fontWeight: tab === key ? 700 : 500,
              }}
              onClick={() => setTab(key)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* 新建题目面板 */}
        {showCreate && (
          <div className="editor-section" style={{ marginBottom: "1.25rem" }}>
            <h3 className="section-title">新建题目</h3>
            <div className="field-row">
              <label className="field-label">题目类型</label>
              <select
                className="editor-input"
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
              >
                <option value="single_choice">单选题</option>
                <option value="multiple_choice">多选题</option>
                <option value="text_input">文本填空</option>
                <option value="number_input">数字填空</option>
              </select>
            </div>
            <div className="field-row">
              <label className="field-label">题目文本</label>
              <input
                className="editor-input"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="请输入题目"
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            </div>
            {newType.includes("choice") && (
              <div className="field-row">
                <label className="field-label">选项</label>
                {newOptions.map((opt, i) => (
                  <div key={opt.option_id} className="option-row">
                    <input
                      className="option-input"
                      value={opt.text}
                      onChange={(e) => {
                        const n = [...newOptions];
                        n[i] = { ...n[i], text: e.target.value };
                        setNewOptions(n);
                      }}
                    />
                    {newOptions.length > 1 && (
                      <button
                        className="remove-opt-btn"
                        onClick={() =>
                          setNewOptions(newOptions.filter((_, j) => j !== i))
                        }
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
                <button
                  className="add-opt-btn"
                  onClick={() =>
                    setNewOptions([
                      ...newOptions,
                      {
                        option_id: `opt${Date.now()}`,
                        text: `选项${newOptions.length + 1}`,
                      },
                    ])
                  }
                >
                  ＋ 添加选项
                </button>
              </div>
            )}
            <div
              style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}
            >
              <button className="save-btn" onClick={handleCreate}>
                创建
              </button>
              <button className="back-btn" onClick={() => setShowCreate(false)}>
                取消
              </button>
            </div>
          </div>
        )}

        {/* 题目列表 */}
        {loading ? (
          <p style={{ color: "#888", textAlign: "center", padding: "2rem" }}>
            加载中...
          </p>
        ) : questions.length === 0 ? (
          <p style={{ color: "#888", textAlign: "center", padding: "2rem" }}>
            {tab === "my"
              ? "暂无自己创建的题目，点击右上角「新建题目」开始创建"
              : tab === "bank"
                ? "题库为空，点击右上角「新建题目」开始创建或先将题目加入题库"
                : "暂无共享题目"}
          </p>
        ) : (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
          >
            {questions.map((q) => {
              const isOpen = expandedId === q.question_id;
              const entry = detailMap[q.question_id];
              const detail = entry?.detail;
              const usage = entry?.usage || [];
              const latest = detail?.versions[detail.versions.length - 1];
              const isShared = detail ? detail.shared_with.length > 0 : false;
              const isSharedWithMe = tab === "shared";

              return (
                <div
                  key={q.question_id}
                  className="question-card"
                  style={{
                    borderLeft: isOpen
                      ? "4px solid var(--brown-dark)"
                      : "4px solid transparent",
                  }}
                >
                  {/* ===== 卡片头部：始终显示 ===== */}
                  <div
                    style={{ padding: "0.85rem 1rem", cursor: "pointer" }}
                    onClick={() => toggleExpand(q.question_id)}
                  >
                    {/* 第一行：类型 + 标题 + 右侧状态 */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                      }}
                    >
                      <span className="q-type-badge">
                        {TYPE_LABEL[q.latest_type] || q.latest_type}
                      </span>
                      <span
                        style={{ fontWeight: 600, fontSize: "1rem", flex: 1 }}
                      >
                        {q.latest_title || "(未命名)"}
                      </span>
                      {/* 右上角状态 */}
                      <span
                        style={{
                          fontSize: "0.75rem",
                          color: "#aaa",
                          flexShrink: 0,
                        }}
                      >
                        v{q.latest_version_number}
                      </span>
                      {isShared && (
                        <span
                          style={{
                            fontSize: "0.72rem",
                            background: "#dbeafe",
                            color: "#1d4ed8",
                            padding: "0.1rem 0.45rem",
                            borderRadius: "999px",
                            flexShrink: 0,
                          }}
                        >
                          已共享
                        </span>
                      )}
                      {!isShared && detail && tab !== "shared" && (
                        <span
                          style={{
                            fontSize: "0.72rem",
                            background: "#f3f4f6",
                            color: "#888",
                            padding: "0.1rem 0.45rem",
                            borderRadius: "999px",
                            flexShrink: 0,
                          }}
                        >
                          未共享
                        </span>
                      )}
                      <span
                        style={{
                          color: "#bbb",
                          fontSize: "0.8rem",
                          marginLeft: "0.25rem",
                        }}
                      >
                        {isOpen ? "▼" : "▶"}
                      </span>
                    </div>

                    {/* 选项内容预览（始终显示） */}
                    {latest ? (
                      <OptionList v={latest} />
                    ) : q.latest_type.includes("choice") ? null : (
                      <div
                        style={{
                          fontSize: "0.8rem",
                          color: "#aaa",
                          marginTop: "0.25rem",
                        }}
                      >
                        {q.latest_type === "text_input"
                          ? "[ 文本输入 ]"
                          : "[ 数字输入 ]"}
                      </div>
                    )}
                  </div>

                  {/* ===== 展开详情 ===== */}
                  {isOpen && (
                    <div
                      style={{
                        borderTop: "1px solid #eee",
                        padding: "0.85rem 1rem",
                      }}
                    >
                      {/* 基本信息 */}
                      <div
                        style={{
                          display: "flex",
                          gap: "1rem",
                          fontSize: "0.8rem",
                          color: "#888",
                          marginBottom: "0.75rem",
                          flexWrap: "wrap",
                        }}
                      >
                        {tab === "shared" && (
                          <span>创建者: {detail?.creator || "..."}</span>
                        )}
                        <span>
                          版本数:{" "}
                          {detail?.latest_version_number ||
                            q.latest_version_number}
                        </span>
                      </div>

                      {/* 操作栏 */}
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: "0.4rem",
                          marginBottom: "0.85rem",
                          alignItems: "center",
                        }}
                      >
                        {tab !== "bank" &&
                          (bankedRefIds.has(q.question_id) ? (
                            <button
                              type="button"
                              disabled
                              className="add-q-btn"
                              style={{
                                background: "#f0fdf4",
                                color: "#16a34a",
                                border: "1px solid #bbf7d0",
                                cursor: "default",
                                opacity: 1,
                              }}
                            >
                              ✅ 已添加入题库
                            </button>
                          ) : (
                            <button
                              className="add-q-btn"
                              onClick={() => handleAddToBank(q.question_id)}
                            >
                              📥 加入我的题库
                            </button>
                          ))}
                        <button
                          className="add-q-btn"
                          onClick={async () => {
                            if (latest) {
                              setVersionTitle(latest.title);
                              setVersionType(latest.type);
                              setVersionOptions(
                                latest.options
                                  ? latest.options.map((o) => ({ ...o }))
                                  : [],
                              );
                            }
                            setShowCrossStatsFor(null);
                            setCrossStats(null);
                            // 检查最新版本是否被已发布/已关闭问卷使用
                            let usageList = usage;
                            if (!entry) {
                              try {
                                usageList = await getQuestionUsage(
                                  q.question_id,
                                );
                              } catch (_) {}
                            }
                            const latestVn =
                              detail?.latest_version_number ||
                              q.latest_version_number;
                            const protectedUsage = usageList.filter(
                              (u) =>
                                u.version_number === latestVn &&
                                (u.survey_status === "published" ||
                                  u.survey_status === "closed"),
                            );
                            if (isSharedWithMe || protectedUsage.length > 0) {
                              // 共享给我的题目或被已发布/已关闭问卷使用的版本 → 只能创建新版本
                              setEditFor(q.question_id);
                              setEditMode("new_version");
                              setEditChoiceFor(null);
                            } else {
                              // 可以选择：修改当前版本 or 创建新版本
                              setEditFor(null);
                              setEditMode(null);
                              setEditChoiceFor(q.question_id);
                            }
                          }}
                        >
                          编辑
                        </button>
                        <button
                          className="add-q-btn"
                          onClick={() => {
                            setEditFor(null);
                            setEditMode(null);
                            setEditChoiceFor(null);
                            handleLoadCrossStats(q.question_id);
                          }}
                        >
                          跨问卷统计
                        </button>
                        {(tab === "my" || tab === "bank") && (
                          <button
                            className="add-q-btn"
                            style={{ color: "#dc2626" }}
                            onClick={() => handleDelete(q.question_id)}
                          >
                            {tab === "bank" ? "移出" : "删除"}
                          </button>
                        )}
                      </div>

                      {/* 编辑方式选择弹窗（需求六：修改时可以决定是否创建新版本） */}
                      {editChoiceFor === q.question_id && (
                        <div
                          style={{
                            background: "#f0f4ff",
                            border: "1px solid #bfdbfe",
                            borderRadius: "0.4rem",
                            padding: "0.85rem",
                            marginBottom: "0.85rem",
                            position: "relative",
                          }}
                        >
                          <button
                            style={{
                              position: "absolute",
                              top: "0.5rem",
                              right: "0.5rem",
                              background: "none",
                              border: "none",
                              cursor: "pointer",
                              fontSize: "1rem",
                              color: "#999",
                              lineHeight: 1,
                            }}
                            onClick={() => setEditChoiceFor(null)}
                          >
                            ✕
                          </button>
                          <div
                            style={{
                              fontWeight: 600,
                              fontSize: "0.85rem",
                              marginBottom: "0.5rem",
                            }}
                          >
                            请选择编辑方式
                          </div>
                          <div
                            style={{
                              fontSize: "0.8rem",
                              color: "#555",
                              marginBottom: "0.6rem",
                            }}
                          >
                            当前最新版本 (v
                            {detail?.latest_version_number ||
                              q.latest_version_number}
                            ) 未被已发布/已关闭的问卷使用，您可以选择：
                          </div>
                          <div style={{ display: "flex", gap: "0.5rem" }}>
                            <button
                              className="save-btn"
                              onClick={() => {
                                setEditChoiceFor(null);
                                setEditFor(q.question_id);
                                setEditMode("in_place");
                              }}
                            >
                              ✏️ 修改当前版本
                            </button>
                            <button
                              className="add-q-btn"
                              style={{ fontWeight: 600 }}
                              onClick={() => {
                                setEditChoiceFor(null);
                                setEditFor(q.question_id);
                                setEditMode("new_version");
                              }}
                            >
                              ＋ 创建新版本
                            </button>
                          </div>
                          <div
                            style={{
                              fontSize: "0.72rem",
                              color: "#888",
                              marginTop: "0.4rem",
                            }}
                          >
                            提示：修改当前版本会直接改变现有内容；创建新版本会保留旧版本不变
                          </div>
                        </div>
                      )}

                      {/* 编辑表单（修改当前版本 or 创建新版本） */}
                      {editFor === q.question_id && editMode && (
                        <div
                          style={{
                            background: "#f9f6f0",
                            padding: "0.85rem",
                            borderRadius: "0.4rem",
                            marginBottom: "0.85rem",
                            position: "relative",
                          }}
                        >
                          <button
                            style={{
                              position: "absolute",
                              top: "0.5rem",
                              right: "0.5rem",
                              background: "none",
                              border: "none",
                              cursor: "pointer",
                              fontSize: "1rem",
                              color: "#999",
                              lineHeight: 1,
                            }}
                            onClick={() => {
                              setEditFor(null);
                              setEditMode(null);
                            }}
                          >
                            ✕
                          </button>
                          <div
                            style={{ fontWeight: 600, marginBottom: "0.4rem" }}
                          >
                            {editMode === "in_place"
                              ? `修改当前版本 (v${detail?.latest_version_number || q.latest_version_number})`
                              : "创建新版本"}
                            {editMode === "new_version" &&
                              (() => {
                                const latestVn =
                                  detail?.latest_version_number ||
                                  q.latest_version_number;
                                const protectedUsage = usage.filter(
                                  (u) =>
                                    u.version_number === latestVn &&
                                    (u.survey_status === "published" ||
                                      u.survey_status === "closed"),
                                );
                                if (isSharedWithMe) {
                                  return (
                                    <span
                                      style={{
                                        fontSize: "0.75rem",
                                        color: "#b45309",
                                        fontWeight: 400,
                                        marginLeft: "0.5rem",
                                      }}
                                    >
                                      （共享给我的题目不能直接修改，只能创建新版本）
                                    </span>
                                  );
                                }
                                return protectedUsage.length > 0 ? (
                                  <span
                                    style={{
                                      fontSize: "0.75rem",
                                      color: "#b45309",
                                      fontWeight: 400,
                                      marginLeft: "0.5rem",
                                    }}
                                  >
                                    （当前版本被 {protectedUsage.length}{" "}
                                    份已发布/关闭问卷使用，只能创建新版本）
                                  </span>
                                ) : null;
                              })()}
                          </div>
                          <div className="field-row">
                            <label className="field-label">题目文本</label>
                            <input
                              className="editor-input"
                              value={versionTitle}
                              onChange={(e) => setVersionTitle(e.target.value)}
                            />
                          </div>
                          {/* 选项编辑（选择题） */}
                          {versionType.includes("choice") && (
                            <div
                              className="field-row"
                              style={{ marginBottom: "0.5rem" }}
                            >
                              <label className="field-label">选项</label>
                              {versionOptions.map((opt, i) => (
                                <div
                                  key={opt.option_id}
                                  className="option-row"
                                  style={{ marginBottom: "0.25rem" }}
                                >
                                  <input
                                    className="option-input"
                                    value={opt.text}
                                    onChange={(e) => {
                                      const next = [...versionOptions];
                                      next[i] = {
                                        ...next[i],
                                        text: e.target.value,
                                      };
                                      setVersionOptions(next);
                                    }}
                                  />
                                  {versionOptions.length > 1 && (
                                    <button
                                      className="remove-opt-btn"
                                      onClick={() =>
                                        setVersionOptions(
                                          versionOptions.filter(
                                            (_, j) => j !== i,
                                          ),
                                        )
                                      }
                                    >
                                      ✕
                                    </button>
                                  )}
                                </div>
                              ))}
                              <button
                                className="add-opt-btn"
                                onClick={() =>
                                  setVersionOptions([
                                    ...versionOptions,
                                    {
                                      option_id: `opt${Date.now()}`,
                                      text: `选项${versionOptions.length + 1}`,
                                    },
                                  ])
                                }
                              >
                                ＋ 添加选项
                              </button>
                            </div>
                          )}
                          <div style={{ display: "flex", gap: "0.5rem" }}>
                            <button
                              className="save-btn"
                              onClick={async () => {
                                if (editMode === "in_place") {
                                  // 原地修改当前版本
                                  try {
                                    await updateVersion(
                                      q.question_id,
                                      detail?.latest_version_number ||
                                        q.latest_version_number,
                                      {
                                        type: versionType,
                                        title: versionTitle,
                                        options: versionType.includes("choice")
                                          ? versionOptions
                                          : undefined,
                                      },
                                    );
                                    setEditFor(null);
                                    setEditMode(null);
                                    flash("当前版本已更新");
                                    loadDetail(q.question_id);
                                    loadQuestions();
                                  } catch (e: any) {
                                    setError(e.message);
                                  }
                                } else {
                                  // 创建新版本
                                  handleCreateVersion(q.question_id);
                                }
                              }}
                            >
                              {editMode === "in_place"
                                ? "保存修改"
                                : "创建新版本"}
                            </button>
                          </div>
                        </div>
                      )}

                      {/* 跨问卷统计（需求八）- 与新版本互斥，显示在操作栏下方 */}
                      {showCrossStatsFor === q.question_id && (
                        <div
                          style={{
                            background: "#f9f6f0",
                            padding: "0.85rem",
                            borderRadius: "0.4rem",
                            marginBottom: "0.85rem",
                            position: "relative",
                          }}
                        >
                          <button
                            style={{
                              position: "absolute",
                              top: "0.5rem",
                              right: "0.5rem",
                              background: "none",
                              border: "none",
                              cursor: "pointer",
                              fontSize: "1rem",
                              color: "#999",
                              lineHeight: 1,
                            }}
                            onClick={() => {
                              setShowCrossStatsFor(null);
                              setCrossStats(null);
                            }}
                          >
                            ✕
                          </button>
                          <div
                            style={{
                              fontWeight: 600,
                              fontSize: "0.85rem",
                              marginBottom: "0.35rem",
                            }}
                          >
                            跨问卷统计
                            {crossStats &&
                              crossStats.question_ref_id === q.question_id && (
                                <span
                                  style={{
                                    fontWeight: 400,
                                    color: "#888",
                                    marginLeft: "0.5rem",
                                  }}
                                >
                                  共 {crossStats.total_answers} 个回答，涉及{" "}
                                  {crossStats.survey_count} 个问卷
                                </span>
                              )}
                          </div>
                          {!crossStats ||
                          crossStats.question_ref_id !== q.question_id ? (
                            <p
                              style={{
                                color: "#aaa",
                                fontSize: "0.8rem",
                                margin: 0,
                              }}
                            >
                              加载中...
                            </p>
                          ) : (
                            <>
                              {crossStats.version_statistics.map((vs) => (
                                <div
                                  key={vs.version_number}
                                  style={{
                                    padding: "0.6rem 0.85rem",
                                    background: "#fff",
                                    border: "1px solid #ede5d5",
                                    borderRadius: "0.4rem",
                                    marginBottom: "0.5rem",
                                  }}
                                >
                                  <div
                                    style={{
                                      fontWeight: 600,
                                      fontSize: "0.83rem",
                                    }}
                                  >
                                    v{vs.version_number} - {vs.title}
                                    <span
                                      style={{
                                        fontWeight: 400,
                                        color: "#888",
                                        marginLeft: "0.5rem",
                                      }}
                                    >
                                      ({vs.total_answers} 回答)
                                    </span>
                                  </div>
                                  {vs.option_statistics &&
                                    vs.option_statistics.map((opt) => (
                                      <div
                                        key={opt.option_id}
                                        style={{
                                          display: "flex",
                                          alignItems: "center",
                                          gap: "0.5rem",
                                          marginTop: "0.2rem",
                                          marginLeft: "0.5rem",
                                        }}
                                      >
                                        <span
                                          style={{
                                            fontSize: "0.8rem",
                                            minWidth: "5rem",
                                          }}
                                        >
                                          {opt.text}
                                        </span>
                                        <div
                                          style={{
                                            flex: 1,
                                            height: "0.5rem",
                                            background: "#e5e1d8",
                                            borderRadius: "999px",
                                            overflow: "hidden",
                                          }}
                                        >
                                          <div
                                            style={{
                                              width: `${opt.percentage}%`,
                                              height: "100%",
                                              background: "var(--brown-dark)",
                                              borderRadius: "999px",
                                            }}
                                          />
                                        </div>
                                        <span
                                          style={{
                                            fontSize: "0.75rem",
                                            color: "#888",
                                            minWidth: "4rem",
                                            textAlign: "right",
                                          }}
                                        >
                                          {opt.count} ({opt.percentage}%)
                                        </span>
                                      </div>
                                    ))}
                                  {vs.text_responses &&
                                    vs.text_responses.length > 0 && (
                                      <div
                                        style={{
                                          fontSize: "0.8rem",
                                          marginTop: "0.3rem",
                                          marginLeft: "0.5rem",
                                          color: "#555",
                                        }}
                                      >
                                        文本回答：
                                        {vs.text_responses
                                          .slice(0, 5)
                                          .join("；")}
                                        {vs.text_responses.length > 5 && "…"}
                                      </div>
                                    )}
                                  {vs.number_statistics && (
                                    <div
                                      style={{
                                        fontSize: "0.8rem",
                                        marginTop: "0.3rem",
                                        marginLeft: "0.5rem",
                                        color: "#555",
                                      }}
                                    >
                                      平均 {vs.number_statistics.average} | 最小{" "}
                                      {vs.number_statistics.min} | 最大{" "}
                                      {vs.number_statistics.max}
                                    </div>
                                  )}
                                </div>
                              ))}
                              {crossStats.surveys.length > 0 && (
                                <div style={{ marginTop: "0.35rem" }}>
                                  <span
                                    style={{
                                      fontSize: "0.8rem",
                                      color: "#888",
                                    }}
                                  >
                                    涉及问卷：
                                  </span>
                                  {crossStats.surveys.map((s) => (
                                    <span
                                      key={s.survey_id}
                                      style={{
                                        fontSize: "0.78rem",
                                        marginRight: "0.6rem",
                                      }}
                                    >
                                      {s.title}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      )}

                      {/* 共享管理（仅我的题库） */}
                      {(tab === "my" || tab === "bank") && detail && (
                        <div
                          style={{
                            background: "#fefcf7",
                            border: "1px solid #ede5d5",
                            borderRadius: "0.4rem",
                            padding: "0.75rem",
                            marginBottom: "0.85rem",
                          }}
                        >
                          <div
                            style={{
                              fontWeight: 600,
                              fontSize: "0.85rem",
                              marginBottom: "0.4rem",
                            }}
                          >
                            共享管理
                          </div>
                          <div style={{ display: "flex", gap: "0.5rem" }}>
                            <input
                              className="editor-input"
                              style={{ flex: 1 }}
                              value={shareUsername}
                              onChange={(e) => setShareUsername(e.target.value)}
                              placeholder="输入用户名"
                              onKeyDown={(e) =>
                                e.key === "Enter" && handleShare(q.question_id)
                              }
                            />
                            <button
                              className="save-btn"
                              onClick={() => handleShare(q.question_id)}
                            >
                              共享
                            </button>
                          </div>
                          {detail.shared_with.length > 0 && (
                            <div
                              style={{
                                marginTop: "0.45rem",
                                display: "flex",
                                flexWrap: "wrap",
                                gap: "0.35rem",
                              }}
                            >
                              {detail.shared_with.map((uid) => (
                                <span
                                  key={uid}
                                  style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    background: "#ede5d5",
                                    borderRadius: "999px",
                                    padding: "0.15rem 0.55rem",
                                    fontSize: "0.8rem",
                                  }}
                                >
                                  {uid}
                                  <button
                                    style={{
                                      background: "none",
                                      border: "none",
                                      color: "#dc2626",
                                      cursor: "pointer",
                                      marginLeft: "0.25rem",
                                      fontSize: "0.85rem",
                                      lineHeight: 1,
                                    }}
                                    onClick={() =>
                                      handleUnshare(q.question_id, uid)
                                    }
                                    title="取消共享"
                                  >
                                    ✕
                                  </button>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* 引用情况（需求六） */}
                      <div style={{ marginBottom: "0.85rem" }}>
                        <div
                          style={{
                            fontWeight: 600,
                            fontSize: "0.85rem",
                            marginBottom: "0.35rem",
                          }}
                        >
                          被以下问卷引用
                        </div>
                        {!detail ? (
                          <p style={{ color: "#aaa", fontSize: "0.8rem" }}>
                            加载中...
                          </p>
                        ) : usage.length === 0 ? (
                          <p style={{ color: "#aaa", fontSize: "0.8rem" }}>
                            暂未被任何问卷使用
                          </p>
                        ) : (
                          <div
                            style={{
                              display: "flex",
                              flexDirection: "column",
                              gap: "0.2rem",
                            }}
                          >
                            {usage.map((u, i) => (
                              <div
                                key={i}
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "0.5rem",
                                  fontSize: "0.83rem",
                                }}
                              >
                                <span style={{ fontWeight: 500 }}>
                                  {u.survey_title}
                                </span>
                                <span
                                  style={{
                                    fontSize: "0.7rem",
                                    padding: "0.05rem 0.35rem",
                                    borderRadius: "999px",
                                    background:
                                      u.survey_status === "published"
                                        ? "#dcfce7"
                                        : u.survey_status === "draft"
                                          ? "#fef9c3"
                                          : "#fee2e2",
                                    color:
                                      u.survey_status === "published"
                                        ? "#166534"
                                        : u.survey_status === "draft"
                                          ? "#854d0e"
                                          : "#991b1b",
                                  }}
                                >
                                  {u.survey_status === "published"
                                    ? "收集中"
                                    : u.survey_status === "draft"
                                      ? "草稿"
                                      : "已关闭"}
                                </span>
                                <span
                                  style={{ fontSize: "0.72rem", color: "#aaa" }}
                                >
                                  使用 v{u.version_number}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* 版本历史（需求四、五） */}
                      <div style={{ marginBottom: "0.85rem" }}>
                        <div
                          style={{
                            fontWeight: 600,
                            fontSize: "0.85rem",
                            marginBottom: "0.35rem",
                          }}
                        >
                          版本历史{" "}
                          {detail && (
                            <span style={{ fontWeight: 400, color: "#aaa" }}>
                              （共 {detail.versions.length} 个版本）
                            </span>
                          )}
                        </div>
                        {!detail ? (
                          <p style={{ color: "#aaa", fontSize: "0.8rem" }}>
                            加载中...
                          </p>
                        ) : (
                          <>
                            {detail.versions.length > 1 && (
                              <VersionTree versions={detail.versions} />
                            )}
                            {detail.versions
                              .slice()
                              .reverse()
                              .map((v) => (
                                <VersionCard key={v.version_number} v={v} />
                              ))}
                          </>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
