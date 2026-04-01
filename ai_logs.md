# AI Usage Logs

## 1

### prompt:

Help us design the database schema, which should be able to support the requirements of the first phase of users while also having certain scalability. Provide the design plans and field descriptions for the core collections (such as Users, Surveys, Responses).

### Result:

AI 提供了一个基础的 MongoDB 集合设计方案 `db_design.md`：

1. **users** collection - 存储用户账户信息，包括用户名、电子邮件、密码哈希值、角色等字段。在用户名和电子邮件上设有唯一索引。
2. **surveys** collection - 存储问卷的元数据以及嵌入的问题数组。每个问题包含问题编号、类型（单选、多选、文本、评分）以及选项和条件跳转逻辑规则。支持诸如允许匿名、允许多次提交、显示结果等调查设置。
3. **responses** collection - 存储单个调查问卷的回复信息，并包含嵌入的答案数组。与调查问卷 ID 和回复者 ID 相关联（匿名回复时该字段可为空）。包含复合索引以用于重复检查和分析查询。

设计理念：

- 调查中的问题嵌入在survey中
- 题目回答内容嵌入在response中
- 用户/调查引用使用 ObjectId（松散关联）

---

## 2

### prompt:

请检查 `db_design.md` 中的数据库设计是否有不合理的地方，对照 `project_requirements.md` 的实验要求逐项比对，并指出需要修正的问题。

### Result:

AI 对原数据库设计进行了全面审查，识别出以下 8 个问题并提出了修正方案：

1. **题型定义与需求不一致**：原设计包含需求中不存在的 `rating` 类型，且没有区分文本填空和数字填空。修正为四种题型：`single_choice` / `multiple_choice` / `text_input` / `number_input`。

2. **缺少按题型区分的校验配置**：新增 `validation` 字段，包含多选题的 `min_selected / max_selected / exact_selected`、文本填空的 `min_length / max_length`、数字填空的 `min_value / max_value / integer_only`。

3. **跳转逻辑结构过于笼统**：原设计只有 `option_id + operator`，无法表达多选包含和数字比较。重新设计为三种条件类型：`select_option`（单选匹配）、`contains_option`（多选包含）、`number_compare`（数字比较，支持 eq/ne/gt/gte/lt/lte/between）。

4. **缺少问卷访问码字段**：新增 `access_code` 字段（唯一索引），用于生成 `/survey/{access_code}` 分享链接。

5. **缺少截止时间字段**：新增 `deadline` 字段。

6. **匿名填写与登录的需求冲突**：需求文档中同时出现"需要先登录"和"支持匿名填写"。经同伴讨论确认，采用"匿名填写时无需登录，非匿名填写时必须登录"的规则，参考了 Google Forms / 问卷星的常见做法。

7. **responses 去重策略不精确**：明确 `survey_id + respondent_id` 复合索引为普通索引（非唯一），去重由业务逻辑根据 `allow_multiple` 设置判断。

8. **responses 集合补充字段**：新增 `is_anonymous`（显式标记匿名提交）和 `user_agent`（辅助信息）字段。

### 修改

在审阅 AI 生成的设计方案并对照第一阶段实验要求后，我人工修改了 `db_design.md` 中的部分数据库设计，主要包括：

1. **增加冗余以优化读写性能**：在 `surveys` 集合加入 `response_count` 派生字段。为避免高频的"查看问卷列表"操作每次都去 `responses` 集合深层统计（countDocuments），用极小的写入成本（提交时同步+1）大幅提升了列表的读取速度。
2. **移除过度设计**：删除了 AI 生成的 `users.role` 和 `surveys.show_results` 字段。严格对照第一阶段需求，目前无需复杂的权限管理与向填写者公开结果的功能。坚守最小可行性原则，剔除超纲设计以保持架构精简，留待第二阶段再做扩展。

---

## 3

### prompt:

基于已确定的技术栈（Python + FastAPI、MongoDB + PyMongo、React + Vite + TypeScript、shadcn/ui + Tailwind CSS、JWT认证）和 `db_design.md` 的完整数据库设计方案，请生成第一阶段所需的所有数据库配置代码与项目骨架，包括 Pydantic 模型定义、FastAPI 应用入口、数据库连接模块、以及完整的项目目录结构初始化。

### Result:

AI 根据选定的技术栈和 `db_design.md` 的设计规范，生成了以下代码文件与项目结构：

1. **Pydantic 数据模型文件**（完全遵循 `db_design.md` 的嵌套结构设计）：
   - `app/models/user.py`：用户模型包括 `UserRegisterRequest`、`UserLoginRequest`、`UserResponse`、`TokenResponse`、`UserInDB`。
   - `app/models/survey.py`：复杂嵌套模型集合，包括：
     - `Question`：题目基础模型
     - `QuestionValidation`：支持多选题、文本填空、数字填空的三类校验规则
     - `QuestionLogic`：跳转逻辑模型（启用/禁用、规则列表）
     - `LogicRule`、`SelectOptionCondition`、`ContainsOptionCondition`、`NumberCompareCondition`、`LogicAction`：支持三种跳转条件类型（单选匹配、多选包含、数字比较）与两种动作类型（跳转、结束）
     - `SurveySettings`：问卷设置（匿名、多次提交）
     - `SurveyCreateRequest`、`SurveyUpdateRequest`、`SurveyResponse`、`SurveyListItem`、`SurveyInDB`：问卷生命周期的各类模型
   - `app/models/response.py`：答卷与统计模型包括：
     - `Answer`：单个题目答案（支持字符串、数组、数字等 Mixed 类型）
     - `ResponseSubmitRequest`、`ResponseDetail`、`ResponseListItem`、`ResponseInDB`：答卷提交与查询模型
     - `OptionStatistic`、`QuestionStatistic`、`SurveyStatistics`：按题型聚合统计的模型

2. **数据库连接与配置模块**：
   - `app/database.py`：PyMongo 单例连接实现、`get_db()` 方法、连接生命周期管理、`init_indexes()` 方法（自动创建 `users`、`surveys`、`responses` 的唯一索引与复合索引）。
   - `app/config.py`：Settings 类读取 `.env` 环境变量（MongoDB URI、数据库名、JWT 密钥、服务端口）。
   - `.env.example` 和 `.env`：配置文件（包含阿里云 MongoDB 连接信息、JWT 密钥、CORS 配置等）。

3. **中间件与工具函数**：
   - `app/middlewares/auth.py`：JWT 认证中间件（验证 token、提取用户信息）。
   - `app/utils/response.py`：统一 API 响应格式（`success_response()`、`error_response()`）与常用错误码定义。

4. **后端应用结构骨架**：
   - `app/main.py`：FastAPI 应用实例化、CORS 跨域中间件配置、生命周期事件钩子（启动时调用 `init_indexes()` 初始化数据库与索引）、路由挂载占位符。
   - `app/routes/` 目录：创建了四个路由模块的占位文件（`auth.py`, `surveys.py`, `responses.py`, `statistics.py`）。
   - `app/services/` 目录：创建了四个业务逻辑层的占位文件（`auth_service.py`, `survey_service.py`, `response_service.py`, `statistics_service.py`）。
   - `backend/tests/` 目录：创建了四个对应模块的测试占位文件（`test_auth.py`, `test_surveys.py`, `test_responses.py`, `test_statistics.py`）。

5. **前端项目结构骨架**：
   - `frontend/src/` 核心目录结构：`components/`, `pages/`, `services/`, `hooks/`, `lib/`, `types/`。
   - `frontend/src/App.tsx` 和 `frontend/src/main.tsx`：前端应用入口文件。
   - `frontend/package.json`：包含 React 18、ReactDOM、Vite 4、TypeScript、ESLint、相关开发依赖的标准配置。

6. **后端依赖与启动配置**：
   - `backend/requirements.txt`：包含 FastAPI、Uvicorn、PyMongo、Pydantic、PyJWT、python-dotenv 等所有必需的 Python 依赖包。

### 修改

在 AI 生成的代码基础上，我人为修改了**MongoDB 连接配置**：

将 `backend/.env.example` 和 `backend/app/config.py` 中的默认 MongoDB URI 从本地 `mongodb://localhost:27017` 修改为实验室阿里云实例连接 `mongodb://ecnu10234500007:ECNU10234500007@dds-uf6cf83b99151cc4-pub.mongodb.rds.aliyuncs.com:3717/admin`，数据库名修改为 `ecnu10234500007`。

---

## 4

### prompt
严格根据现有项目情况，完成API 接口文档，包括注册 / 登录、创建问卷 / 获取问卷 /
编辑问卷 / 发布问卷 / 关闭问卷、获取公开问卷 / 提交答卷、获取统计结果、统一请求体 / 响应体格式等内容

### result

AI 根据 `system_docs.md` 的项目需求和功能描述，生成了一份完整的 API 接口文档 `api_docs.md`，涵盖以下内容：

1. **统一约定**：基础协议、鉴权方式、统一 JSON 响应格式（code/message/data）、HTTP 状态码、错误码表。
2. **用户认证接口**：注册（POST /auth/register）和登录（POST /auth/login）的请求体与响应结构。
3. **问卷管理接口**：创建、获取列表、获取详情、编辑、发布、关闭、删除共 7 个接口，包含请求体、响应示例和分页参数。
4. **问卷填写接口**：通过访问码获取公开问卷（GET /public/surveys/{access_code}）和提交答卷（POST /responses），支持匿名/登录两种模式。
5. **统计分析接口**：问卷整体统计和单题统计两个接口。
6. **题目类型与跳转逻辑**：四种题型（单选、多选、文本填空、数字填空）的结构定义、校验规则和答案格式，以及基于选项和数值范围的跳转逻辑说明。
7. **接口清单总表**：汇总所有接口的方法、路径、鉴权要求。

### 修改

在审阅 AI 生成的 API 文档后，我对照 `db_design.md` 的数据库设计进行了以下人工修改：

1. **统一字段命名与 db_design 对齐**：将 AI 生成的 `allow_anonymous`/`allow_multiple_submissions` 扁平字段改为嵌套在 `settings` 对象中（`settings.allow_anonymous`/`settings.allow_multiple`），与数据库文档结构保持一致。将 `min_selections`/`max_selections` 改为 `min_selected`/`max_selected`，与 db_design 的 validation 字段名一致。
2. **简化答案格式**：将 AI 生成的嵌套答案结构（如 `{"selected_options": ["opt1"]}`、`{"text": "..."}`、`{"number": 85}`）简化为直接值（`"opt1"`、`["opt1","opt3"]`、`"文本"`、`85`），与 db_design 中 `answer: Mixed` 的设计一致。
3. **补充访问控制规则**：新增 2.4 节，明确条件鉴权规则、创建者权限、发布状态限制、截止时间校验、重复提交控制等业务规则。
4. **补充问卷状态与编辑规则**：新增 2.5 节，明确状态流转（draft → published → closed）和编辑限制（已有答卷时不允许修改题目结构）。
5. **调整登录响应结构**：将 AI 生成的 `token` 字段改为 `access_token` + `token_type` 的标准 OAuth2 风格，并在响应中嵌套完整的 `user` 对象。
6. **精简文档结构**：移除了 AI 生成的冗余章节（题目类型详细说明、跳转逻辑详细说明、附录），将核心信息整合到接口示例中，使文档更紧凑。
7. **补充 `completion_time` 字段**：在提交答卷请求体中增加 `completion_time`（完成耗时秒数），与 db_design 中 responses 集合的字段对齐。

---

## 5
