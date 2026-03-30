# AI Usage Logs

## 1

### prompt:

Help us design the database schema, which should be able to support the requirements of the first phase of users while also having certain scalability. Provide the design plans and field descriptions for the core collections (such as Users, Surveys, Responses).

### Result:

为问卷系统设计了三个主要的 MongoDB 数据集合：

1. **users** collection - 存储用户账户信息，包括用户名、电子邮件、密码哈希值、角色等字段。在用户名和电子邮件上设有唯一索引。
2. **surveys** collection - 存储问卷的元数据以及嵌入的问题数组。每个问题包含问题编号、类型（单选、多选、文本、评分）以及选项和条件跳转逻辑规则。支持诸如允许匿名、允许多次提交、显示结果等调查设置。
3. **responses** collection - 存储单个调查问卷的回复信息，并包含嵌入的答案数组。与调查问卷 ID 和回复者 ID 相关联（匿名回复时该字段可为空）。包含复合索引以用于重复检查和分析查询。
   设计理念：

- 调查中的问题嵌入在survey中
- 题目回答内容嵌入在response中
- 用户/调查引用使用 ObjectId（松散关联）

### 所做的修改

创建了 `db design.md` 文件，记录了这三个集合的结构设计与字段说明。

---

## 2

### prompt:

请检查 `db design.md` 中的数据库设计是否有不合理的地方，对照 `Project Documentation.md` 的实验要求逐项比对，并指出需要修正的问题。

### Result:

AI 对原数据库设计进行了全面审查，识别出以下 9 个问题并提出了修正方案：

1. **题型定义与需求不一致**：原设计包含需求中不存在的 `rating` 类型，且没有区分文本填空和数字填空。修正为四种题型：`single_choice` / `multiple_choice` / `text_input` / `number_input`。

2. **缺少按题型区分的校验配置**：新增 `validation` 字段，包含多选题的 `min_selected / max_selected / exact_selected`、文本填空的 `min_length / max_length`、数字填空的 `min_value / max_value / integer_only`。

3. **跳转逻辑结构过于笼统**：原设计只有 `option_id + operator`，无法表达多选包含和数字比较。重新设计为三种条件类型：`select_option`（单选匹配）、`contains_option`（多选包含）、`number_compare`（数字比较，支持 eq/ne/gt/gte/lt/lte/between）。

4. **缺少问卷访问码字段**：新增 `access_code` 字段（唯一索引），用于生成 `/survey/{access_code}` 分享链接。

5. **缺少截止时间字段**：新增 `deadline` 字段。

6. **匿名填写与登录的需求冲突**：需求文档中同时出现"需要先登录"和"支持匿名填写"。经同伴讨论确认，采用"匿名填写时无需登录，非匿名填写时必须登录"的规则，参考了 Google Forms / 问卷星的常见做法。

7. **responses 去重策略不精确**：明确 `survey_id + respondent_id` 复合索引为普通索引（非唯一），去重由业务逻辑根据 `allow_multiple` 设置判断。

8. **responses 集合补充字段**：新增 `is_anonymous`（显式标记匿名提交）和 `user_agent`（辅助信息）字段。

9. **移除过度设计**：移除了 users 中的 `role` 字段和 surveys 中的 `show_results` 设置，第一阶段需求不涉及这些功能，留作未来扩展方向。

同时补充了"为什么适合 MongoDB"、"为什么不用关系数据库结构"、"扩展性考量"等设计说明章节。

### 所做的修改

根据审查结果全面修订了 `db design.md`，具体改动如上所述，本次属于架构设计审查与优化。
