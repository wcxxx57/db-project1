# 第二阶段

## 1

### prompt

根据第二阶段实验要求 `第二阶段实验要求.md` 中的 8 个新增需求（题目复用、共享、版本管理、修改历史、多版本共存、引用反查、题库、跨问卷统计），在第一阶段数据库设计（`数据库设计.md`）的基础上，设计第二阶段的数据库方案。

### result

我在分析了第二阶段 8 个需求后，自行完成了 `db_design2.md` 初版设计，核心决策包括：

1. **新增 `questions` 集合**：独立存储题目实体，采用内嵌版本模式（Embedded Versioning Pattern），每个题目文档包含 `q_id`（业务唯一标识）、`access_control`（创建者/共享/题库权限）和 `versions` 数组（全部历史版本）。

2. **`surveys` 集合修改**：`questions` 数组从嵌入完整题目内容改为引用 `q_id + version_number`，仅保留问卷局部上下文（`question_id` 局部题号、`order` 顺序、`logic` 跳转逻辑）。

3. **`responses` 集合修改**：`answers` 数组新增 `q_id` 和 `version_number` 字段，支持跨问卷统计和版本追踪。

4. **设计中留下两个待确认问题**：
   - 是否需要独立的「题库」collection？
   - survey 中是否要嵌入 questions 内容？

---

## 2

### prompt

请帮我分析 `db_design2.md` 的设计是否合理，并回答两个不确定的问题：
1. 是否需要独立题库 collection？主要是对于"题库管理"的理解，到底怎样算管理。
2. survey 中是否要嵌入 questions？不嵌入的前提是"旧版本不能删、不能改、始终可查"，要使得数据库查询等操作性能越快越好。

### result

AI 对 `db_design2.md` 进行了全面评审，逐一验证了 8 个需求的覆盖情况，并回答了两个核心问题：

**问题一：是否需要独立题库 collection？**
- **结论：不需要**。需求中的"题库管理"本质是用户的个人收藏夹（加入/移除/选题），通过 `banked_by` 数组即可实现（加入 → `$addToSet`，移除 → `$pull`，查询 → `find({"access_control.banked_by": user_id})`）。只有当需求要求"用户可以创建多个命名分类题库"时才需要独立 collection，当前需求没有这个要求。

**问题二：survey 中是否嵌入 questions？**
- **结论：不嵌入（引用方案）是正确选择**。在"旧版本不删不改"的不变量前提下，引用方案仅多 1 次批量查询（`$in` 查 questions），但换来跨问卷统计（需求八）和反查引用（需求六）成为简单索引查询，以及题目共享（需求二）的零冗余。

**同时指出了设计中需要改进的 5 个细节**：

1. **🔴 `responses.answers` 中 `selected_option_ids` 和 `answer` 字段冗余**：第一阶段的 `answer: Mixed` 已可表示所有题型答案，`selected_option_ids` 应删除。
2. **🔴 缺少索引设计**：需要补充 `questions.q_id`（唯一索引）、`access_control.creator/shared_with/banked_by`（查询索引）、`surveys.questions.q_id`（多键索引，反查引用）、`responses.answers.q_id`（多键索引，跨问卷统计）。
3. **🟡 `questions` 缺少 `_id` 字段标注**：应显式标注 `_id: ObjectId` 作为 MongoDB 主键。
4. **🟡 `latest_version_number` 并发安全**：建议使用 `find_one_and_update` + `$inc` 原子操作保证版本号不冲突。
5. **🟡 权限模型需要细化**：`shared_with` 用户的权限边界不明确。

**额外讨论确认的决策**：
- **权限模型**：确认 `shared_with` 用户仅有只读使用权（可引用、可加入题库），不能创建新版本，只有 `creator` 可以修改题目。
- **题目删除策略**：需求未要求删除题目，确认不实现删除功能，仅支持"从题库移除"（`$pull banked_by`），与"保留一切、版本不可变"的设计精神一致，且对数据库 schema 无影响。

### 修改

根据 AI 的评审意见，我对 `db_design2.md` 进行了以下修改：

1. **删除冗余字段**：移除 `responses.answers.selected_option_ids`，统一使用 `answer: Mixed`。
2. **补充完整索引设计**：为 `questions`、`surveys`、`responses` 三个集合补充了所有新增索引及其用途说明。
3. **显式标注 `_id`**：在 `questions` 集合中显式标注 `_id: ObjectId`。
4. **补充并发安全说明**：增加 `find_one_and_update` + `$inc` 原子操作的代码示例。
5. **明确权限模型**：在 `shared_with` 字段注释中明确标注"只读使用权"。

---

## 3

### prompt

先阅读项目的现有文件及第一阶段代码，根据 `需求变更.md` 中的开发阶段及用户需求要求，依据 `数据库设计2.md` 中的数据模型设计，更改完善 `第二阶段实现计划.md`。

### What code was obtained

重写了 `第二阶段实现计划.md`，结合现有第一阶段代码结构，明确了第二阶段的实际落地方案：去掉独立题库 collection 方案，改为基于 `questions.access_control.banked_by` 的个人题库；将问卷改造为题目版本引用模式；补充后端/前端实施阶段、一次性数据迁移、测试与文档更新顺序。

### Were any modifications made/What modifications were made by people based on AI's result

目前暂无。

---

## 4

### prompt

编辑问卷题目时：1）用户新建的题（非题库选取）在右下角加"加入我的题库"按钮，点击后将当前用户加入该题目的 banked_by 数组，不点则 banked_by 为空；2）用户从题库选的题如果修改了内容，右下角出现"创建新版本保存修改"按钮，点击后创建新版本，等效于题目管理界面的版本操作。

### What code was obtained

修改 `frontend/src/components/SurveyEditor.tsx`：
- 新增状态追踪题目来源（newlyCreatedQids）、是否已加入题库（bankedQids）、原始内容快照（originalContent）、版本保存状态（versionSavedQids）
- 新增 `isQuestionModified` 函数通过深比较检测题库题目是否被修改
- 新增 `handleAddToBank` 调用 addToBank API 将题目加入用户题库
- 新增 `handleCreateNewVersion` 调用 createNewVersion API 创建新版本并更新引用版本号和原始内容快照
- 在题目编辑区右下角渲染对应按钮

### Were any modifications made/What modifications were made by people based on AI's result

目前暂无。

---

## 5

### prompt

为什么每在编辑问卷的时候增加一个题目，题目管理里面就会莫名其妙多一个"新题目"，没有点过加入题库。

### What code was obtained

修复了题目管理"我的题库"tab 的数据源问题：
- `QuestionManager.tsx`："我的题库"tab 从 `getMyQuestions()`（按 creator 查询）改为 `getBankedQuestions()`（按 banked_by 查询），确保只有用户主动加入题库的题目才会出现
- `QuestionManager.tsx`：`handleCreate` 创建题目后自动调用 `addToBank` 加入题库
- `SurveyEditor.tsx`：选题面板"我的题库"tab 也从 `getMyQuestions` 改为 `getBankedQuestions`

### Were any modifications made/What modifications were made by people based on AI's result

目前暂无。

---

## 6

### prompt

1.题库删除题目时若有问卷使用要提醒用户，确认后级联删除问卷中的引用；2.共享列表和创建者显示用户名而非用户ID；3.版本数据模型去掉required字段；4.版本卡片小字改为显示版本创建者用户名

### What code was obtained

后端 `question_service.py`：
- 新增 `_resolve_usernames()` 批量 user_id→username 解析
- `_serialize_question_detail` 和 `_serialize_question_list_item`：creator、shared_with、updated_by 全部解析为用户名
- `delete_question`：改为级联删除，从所有引用该题目的问卷中 pull 并重排 order，返回受影响问卷列表
- 所有版本相关函数移除 required 字段

后端 `question.py` 模型：所有请求/响应模型移除 required 字段

后端 `survey_service.py`：`_resolve_question_refs` 移除 required 解析

前端 `QuestionManager.tsx`：
- `handleDelete` 先查使用情况，confirm 中列出受影响问卷名称
- `VersionCard` 小字从"必答/选答"改为"创建者: xxx"
- 新版本表单移除"必答题"勾选框

前端 `SurveyEditor.tsx`：选题面板版本显示改为创建者用户名；createNewVersion 调用移除 required

前端 `types/index.ts`：QuestionVersion、CreateQuestionRequest、CreateVersionRequest 移除 required

### Were any modifications made/What modifications were made by people based on AI's result

目前暂无。

---

## 7

### prompt

修改题目版本逻辑：保存问卷时如果有题目被修改就自动生成递增新版本，保留历史、不影响其他问卷引用，方便版本追溯和统计

### What code was obtained

重构 `SurveyEditor.tsx` 的 `handleSave`：
- 保存时遍历所有题目，对比 originalContent 快照检测修改
- 临时题目（`__temp_` 前缀）创建 question 文档
- 已有题目如有修改，自动调用 `createNewVersion` 创建新版本，更新引用版本号
- 保存后刷新 originalContent 快照为新基准
- 提示信息显示自动创建了几个新版本
- 移除手动"创建新版本保存修改"按钮，改为实时修改提示文字
- `addQuestion` 改为同步本地操作（不立即调用后端），延迟到保存/加入题库时创建

### Were any modifications made/What modifications were made by people based on AI's result

目前暂无。

---

## 8

### prompt

编辑问卷时增加可以选择其他/历史版本的功能

### What code was obtained

在 `SurveyEditor.tsx` 中新增版本切换功能：
- 新增 `versionPickerQid/versionPickerData/versionPickerLoading` 状态
- `toggleVersionPicker`：点击"切换版本"按钮时调用 `getQuestionDetail` 加载该题目全部历史版本
- `switchVersion`：选定版本后替换当前题目的 type/title/options/validation/version_number，同时更新 originalContent 快照避免误判为修改
- UI：题目展开后标题字段下方显示"切换版本（当前 vN）"按钮，展开后显示倒序版本列表，当前版本高亮标记，其他版本可点击"切换到此版本"

### Were any modifications made/What modifications were made by people based on AI's result

目前暂无。

---

## 9

### prompt

1.题库VersionCard去掉"恢复此版本"按钮；编辑问卷切换版本时要展示各版本的选项详情；2.题目管理版本历史增加 v1→v2→v3（含分支）的版本关系树；3.跨问卷统计和新版本都做成可展开/收起的卡片，右上角有✕关闭按钮

### What code was obtained

`QuestionManager.tsx`：
- `VersionCard` 移除 `onRestore` 按钮，改为纯展示
- 新增 `VersionTree` 组件，基于 `parent_version_number` 递归渲染 Unicode 树形结构（├──/└──/│），直观展示版本分支关系
- 新版本表单添加右上角 ✕ 关闭按钮，移除底部"取消"按钮
- 跨问卷统计改为可切换卡片（`showCrossStatsFor` 状态），添加右上角 ✕ 关闭按钮
- 移除无用的 `handleRestore` 和 `restoreVersion` import

`SurveyEditor.tsx`：
- 版本切换面板中每个版本增加选项详情展示（单选○/多选☐ + 选项文本），文本/数字类型显示占位提示

### Were any modifications made/What modifications were made by people based on AI's result

目前暂无。

---

## 10

### prompt

1.跨问卷统计卡片移到操作栏下方（和新版本同级），两者互斥（点一个自动关另一个）；2.版本关系图改为横向箭头流（v1→v2→v3），分支换行用↘标注，不显示title

### What code was obtained

`QuestionManager.tsx`：
- 跨问卷统计卡片从版本历史下方移到新版本表单旁边（操作栏下方）
- 新版本按钮点击时自动关闭跨问卷统计，反之亦然
- `VersionTree` 重写为横向箭头流：主链水平排列 v1→v2→v3，分支另起一行用↘+缩进对齐分叉点，主链棕色标签、分支橙色标签

### Were any modifications made/What modifications were made by people based on AI's result

目前暂无。