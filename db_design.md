# MongoDB 数据库设计文档

## 设计总览

本系统采用三个核心集合：`users`、`surveys`、`responses`，分别存储用户信息、问卷（含嵌入式题目）和答题记录（含嵌入式答案）。

**核心设计原则：**

- 题目嵌入在问卷文档中（强一对多关系，总是一起查询，避免 JOIN）
- 答案嵌入在答题记录中（原子操作单元，不可拆分）
- 用户与问卷/答题之间使用 ObjectId 引用（松散耦合，便于扩展）
- 校验规则、跳转逻辑均以数据驱动，不硬编码在程序中

---

## 集合（Collections）设计

### 1. users（用户）集合

存储用户账户信息。

```json
{
  "_id": ObjectId,
  "username": String,        // 用户名（唯一）
  "password_hash": String,   // 密码哈希值
  "created_at": DateTime     // 注册时间
}
```

**索引：**

- `username`（唯一索引）

**设计说明：**

- 第一阶段账号字段保持最小集合：用户名、密码哈希、注册时间。
- 注册密码约束为 8-128 字符。
- 第一阶段不需要角色系统，暂不添加 `role` 字段，避免过度设计；如果第二阶段有权限需求，可以直接加字段，MongoDB 的 schema-less 特性天然支持。

---

### 2. surveys（问卷）集合

存储问卷元数据、设置和嵌入的题目数组。

```json
{
  "_id": ObjectId,
  "title": String,               // 问卷标题
  "description": String,         // 问卷说明
  "creator_id": ObjectId,        // 创建者 ID（关联 users._id）
  "access_code": String,         // 公开访问码，用于生成分享链接 /survey/{access_code}
  "status": String,              // 状态："draft"（草稿）/ "published"（已发布）/ "closed"（已关闭）
  "created_at": DateTime,        // 创建时间
  "updated_at": DateTime,        // 更新时间
  "deadline": DateTime,          // 截止时间（null 表示无截止）
  "response_count": Number,      // 已收集答卷数（派生字段，每次提交成功后 +1，用于列表页展示）
  "settings": {
    "allow_anonymous": Boolean,  // 是否允许匿名填写（true = 统计结果隐藏答题者身份）
    "allow_multiple": Boolean    // 是否允许同一用户多次提交
  },
  "questions": [                 // 嵌入的题目数组
    {
      "question_id": String,     // 题目唯一标识，如 "q1", "q2"
      "type": String,            // 题目类型："single_choice" / "multiple_choice" / "text_input" / "number_input"
      "title": String,           // 题目文本
      "required": Boolean,       // 是否必答
      "order": Number,           // 显示顺序

      // ---- 选项（仅 single_choice / multiple_choice 使用）----
      "options": [
        {
          "option_id": String,   // 选项标识，如 "opt1", "opt2"
          "text": String         // 选项文本
        }
      ],

      // ---- 校验规则（按题型区分）----
      "validation": {
        // 多选题校验
        "min_selected": Number,    // 最少选择数量（仅 multiple_choice）
        "max_selected": Number,    // 最多选择数量（仅 multiple_choice）
        "exact_selected": Number,  // 必须选择的精确数量（仅 multiple_choice，优先级高于 min/max）

        // 文本填空校验
        "min_length": Number,      // 最少字数（仅 text_input）
        "max_length": Number,      // 最多字数（仅 text_input）

        // 数字填空校验
        "min_value": Number,       // 最小值（仅 number_input）
        "max_value": Number,       // 最大值（仅 number_input）
        "integer_only": Boolean    // 是否必须为整数（仅 number_input）
      },

      // ---- 跳转逻辑 ----
      "logic": {
        "enabled": Boolean,        // 是否启用跳转逻辑
        "rules": [
          {
            "condition": {
              "type": String,      // 条件类型："select_option" / "contains_option" / "number_compare"
              // --- select_option（单选匹配）---
              "option_id": String,           // 当选择了该选项时触发


              // --- contains_option（多选包含）---
              "option_ids": [String],        // 当选择的选项中包含这些时触发
              "match_type": "any", // "any" 代表(OR), "all" 代表 (AND)

              // --- number_compare（数字比较）---
              "operator": String,            // 操作符："eq" / "ne" / "gt" / "gte" / "lt" / "lte" / "between"
              "value": Number,               // 比较值（用于 eq/ne/gt/gte/lt/lte）
              "min_value": Number,           // 区间最小值（用于 between）
              "max_value": Number            // 区间最大值（用于 between）
            },
            "action": {
              "type": String,                // 动作类型："jump_to" / "end_survey"
              "target_question_id": String   // 跳转目标题目 ID（仅 jump_to 使用）
            }
          }
        ]
      }
    }
  ]
}
```

**索引：**

- `creator_id`（查询用户自己的问卷）
- `access_code`（唯一索引，通过分享链接快速定位问卷）
- `status`（按状态筛选）
- `created_at`（降序，用于列表排序）

**设计说明：**

1. **题目嵌入问卷文档**：题目与问卷是强一对多关系，业务上总是一起查询和展示，嵌入可避免 JOIN，提高读取性能。这正是 MongoDB 文档模型的优势所在。

2. **`access_code` 字段**：需求要求通过 `/survey/xxxxxx` 链接分发问卷。使用独立的短码字段（而非直接暴露 `_id`），更友好且安全，也便于后续实现自定义链接。

3. **`deadline` 字段**：需求明确要求"设置问卷截止时间"，到期后系统应拒绝新的提交。

4. **题型精确划分**：需求要求支持单选、多选、文本填空、数字填空四种题型。原设计中的 `rating` 类型不在需求范围内，已移除；将原来模糊的 `text` 拆分为 `text_input`（文本填空）和 `number_input`（数字填空），以便为不同题型配置不同的校验规则。

5. **`validation` 字段**：需求明确要求多选题限制选择数量、文本限制字数、数字限制范围和整数约束。将这些校验规则以数据形式存在文档中，后端读取后执行校验，避免硬编码。不同题型只使用各自相关的字段，其余字段为空即可，MongoDB 的灵活 schema 天然支持这种设计。

6. **跳转逻辑条件模型**：需求要求支持根据单选、多选、数字填空结果跳转。原设计只有 `option_id + operator` 过于笼统，现在按条件类型分为三种：
   - `select_option`：单选匹配某选项
   - `contains_option`：多选包含某些选项
   - `number_compare`：数字比较（支持 eq/ne/gt/gte/lt/lte/between）

7. **匿名填写规则**：填写问卷时用户必须先登录。其中 `allow_anonymous` 字段控制统计结果的展示规则：若 `allow_anonymous = true`，则统计结果中隐藏答题者身份信息；若 `allow_anonymous = false`，则统计结果中显示答题者身份（用户名）。

8. **`response_count` 派生字段**：为提升问卷列表页的查询性能，在 `surveys` 中冗余保存已收集答卷数。该字段不作为源数据，而是在每次答卷提交成功后由后端同步 +1 更新。核心答题数据仍以 `responses` 集合中的原始记录为准。若出现计数不一致，可通过重新统计 `responses` 修复。

---

### 3. responses（答题记录）集合

存储单次问卷填写的完整结果。

```json
{
  "_id": ObjectId,
  "survey_id": ObjectId,         // 关联 surveys._id
  "respondent_id": ObjectId,     // 答题者 ID（关联 users._id；匿名填写时为 null）
  "is_anonymous": Boolean,       // 是否为匿名提交
  "submitted_at": DateTime,      // 提交时间
  "ip_address": String,          // IP 地址（辅助匿名场景下的基础风控）
  "user_agent": String,          // 浏览器 UA（辅助信息）
  "answers": [                   // 嵌入的答案数组
    {
      "question_id": String,     // 对应 surveys.questions[].question_id
      "answer": Mixed            // 答案值，根据题型不同：
                                 // - single_choice: String（选中的 option_id）
                                 // - multiple_choice: [String]（选中的 option_id 数组）
                                 // - text_input: String（文本内容）
                                 // - number_input: Number（数字值）
    }
  ],
  "completion_time": Number      // 完成问卷所用秒数（可选）
}
```

**索引：**

- `survey_id` + `submitted_at`（复合索引，用于按时间查询某问卷的答题记录和统计）
- `survey_id` + `respondent_id`（复合索引，用于查询某用户是否已提交过该问卷；注意：不设为唯一索引，因为 `allow_multiple` 允许重复提交）
- `respondent_id`（单独索引，用于查询某用户的所有答题记录）

**设计说明：**

1. **答案嵌入答题记录**：一次提交的所有答案属于同一个原子操作单元，总是一起存取，嵌入是最自然的 MongoDB 建模方式。

2. **`answer` 使用 Mixed 类型**：不同题型的答案格式不同（字符串 / 数组 / 数字），MongoDB 天然支持灵活类型。校验由后端根据对应 question 的 `type` 和 `validation` 规则进行，不依赖数据库层面的类型约束。

3. **`is_anonymous` 字段**：虽然可以通过 `respondent_id == null` 来判断是否匿名，但显式存储一个布尔字段语义更清晰，也便于后续统计查询。

4. **去重策略**：`survey_id + respondent_id` 复合索引是普通索引（非唯一），是否允许重复提交由业务逻辑根据 `surveys.settings.allow_multiple` 判断。匿名场景下 `respondent_id` 为 null，重复控制可通过 `ip_address` / `session` 辅助实现（第一阶段暂不强制）。

5. **`ip_address` 和 `user_agent`**：为匿名填写场景提供基础的辅助追踪信息，不作为核心去重依据，但为后续阶段可能的防刷策略预留数据。

---

## 为什么适合 MongoDB

1. **题目结构灵活**：不同题型有不同的字段（选项、校验规则、跳转条件），MongoDB 的文档模型天然支持这种异构嵌套，无需像关系数据库那样拆出多张关联表。
2. **嵌入式文档减少查询**：题目嵌入问卷、答案嵌入答题记录，一次查询即可获取完整数据，无需 JOIN。
3. **Schema 灵活演化**：第二阶段需求变更时可以直接添加新字段，无需 ALTER TABLE 或数据迁移。
4. **校验和逻辑数据驱动**：`validation` 和 `logic` 以 JSON 结构存储在文档中，后端读取执行，完全避免硬编码。

## 为什么不用关系数据库结构

1. 关系数据库需要将题目、选项、校验规则、跳转规则分别建表，通过外键关联，查询时需要多次 JOIN，复杂度高。
2. 不同题型的校验字段差异大，关系数据库需要大量可空列或多态表设计，不够自然。
3. 问卷结构在发布后相对稳定（主要是读操作），非常适合 MongoDB 的嵌入式文档模型。

---

## 扩展性考量

1. **关注点分离**：用户、问卷、答题记录分别在不同集合中，可独立扩展和优化。
2. **嵌入 vs 引用的权衡**：
   - 题目嵌入问卷（紧密耦合，总是一起查询）
   - 答案嵌入答题记录（原子操作单元）
   - 用户与问卷/答题之间使用 ObjectId 引用（松散耦合）
3. **未来可扩展方向**：
   - 新增 `survey_templates` 集合用于问卷模板
   - 新增 `analytics` 集合用于统计缓存
   - 在 `surveys` 中增加 `collaborators` 数组支持协同编辑
   - 在 `users` 中增加 `role` 字段支持权限控制
   - 在 `questions` 中增加 `version` 字段支持题目版本管理

---

## 问卷修改策略

**第一阶段设计决策：**

本系统允许在 `closed`（已关闭）状态下修改问卷，包括题目结构，以提供最大的灵活性。

**设计考量：**
- `draft` 状态：可以自由编辑（未发布，无答卷数据）
- `published` 状态：不可编辑（正在收集答卷，保证数据一致性）
- `closed` 状态：可以编辑（已停止收集，创建者可能需要修正错误或调整问卷）

**潜在风险与应对：**
- **风险**：修改题目结构后，历史答卷中的 `question_id` 或 `option_id` 可能找不到对应定义
- **应对**：统计代码实现了容错逻辑，会自动忽略找不到定义的题目和选项，并在统计结果中添加警告信息
- **建议**：前端在编辑已有答卷的问卷时给出警告提示，提醒用户修改题目结构的风险

**数据一致性保护机制：**
1. 统计时检测孤儿答案（对应题目已被删除的答案）
2. 统计时检测未知选项（对应选项已被删除的答案）
3. 在统计结果中添加警告信息，告知用户数据不完整的原因
4. 前端编辑页面显示警告横幅，提醒用户谨慎修改

**为第二阶段预留的扩展点：**

如果第二阶段需求要求更严格的数据一致性保护或更灵活的修改能力，可以：
1. 引入版本管理机制（每次修改创建新版本，`questions_v1`, `questions_v2`）
2. 答卷记录关联到具体版本（`question_version` 字段）
3. 统计时按版本分别统计，或合并统计时智能匹配题目
4. 支持问卷分支（fork）功能，修改时自动创建新问卷
5. 增加 `response_count > 0` 时的严格保护模式（禁止修改题目结构）
