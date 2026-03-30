### 核心集合（Collections）设计

**1. users (用户) 集合**

存储用户账户信息。

```json
{
  "_id": ObjectId,
  "username": String,        // 用户名 (唯一，已建立索引)
  "email": String,           // 邮箱 (唯一，已建立索引)
  "password_hash": String,   // 密码哈希值
  "created_at": DateTime,    // 创建时间
  "updated_at": DateTime,    // 更新时间
  "role": String             // 角色 ("admin" 或 "user"，用于未来基于角色的权限控制)
}
```

**索引 (Indexes):**
* `username` (唯一索引)
* `email` (唯一索引)

---

**2. surveys (问卷) 集合**

存储问卷元数据和结构。

```json
{
  "_id": ObjectId,
  "title": String,               // 问卷标题
  "description": String,         // 问卷说明
  "creator_id": ObjectId,        // 创建者 ID (关联 users 集合的 _id)
  "status": String,              // 状态 ("draft" 草稿, "published" 已发布, "closed" 已关闭)
  "created_at": DateTime,        // 创建时间
  "updated_at": DateTime,        // 更新时间
  "settings": {
    "allow_anonymous": Boolean,  // 是否允许匿名填写
    "allow_multiple": Boolean,   // 是否允许单个用户多次提交
    "show_results": Boolean      // 是否向答题者展示结果
  },
  "questions": [                 // 嵌套的题目数组
    {
      "question_id": String,     // 在问卷内唯一的标识，例如 "q1", "q2"
      "type": String,            // 题目类型："single_choice" (单选), "multiple_choice" (多选), "text" (填空), "rating" (评分)
      "title": String,           // 题目文本
      "required": Boolean,       // 是否必答
      "options": [               // 选项数组 (用于选择类题目)
        {
          "option_id": String,   // 选项标识，例如 "opt1", "opt2"
          "text": String         // 选项文本
        }
      ],
      "logic": {                 // 条件跳转逻辑
        "enabled": Boolean,      // 是否启用逻辑
        "rules": [               // 规则数组
          {
            "condition": {
              "option_id": String,     // 如果选择了该选项
              "operator": String       // 操作符："equals" (等于), "contains" (包含) 等
            },
            "action": {
              "type": String,          // 动作类型："jump_to" (跳转至), "end_survey" (结束问卷)
              "target_question_id": String  // 要跳转到的目标题目 ID
            }
          }
        ]
      },
      "order": Number            // 显示顺序
    }
  ]
}
```

**索引 (Indexes):**
* `creator_id`
* `status`
* `created_at` (降序 descending)

**设计思路 (Design Rationale):**
* **题目被嵌套在问卷文档中**，因为它们之间具有强烈的“一对多”关系，并且业务上总是一起被查询出来。
* 这种嵌套避免了类似关系型数据库的 JOIN 操作，大幅提高了读取性能。
* `question_id` 和 `option_id` 使用字符串标识符，以便更轻松地在前后端实现条件跳转逻辑。

---

**3. responses (答题记录) 集合**

存储单个用户对问卷的答题结果。

```json
{
  "_id": ObjectId,
  "survey_id": ObjectId,         // 关联 surveys 集合的 _id
  "respondent_id": ObjectId,     // 答题者 ID (关联 users 集合的 _id，若是匿名填写则为 null)
  "submitted_at": DateTime,      // 提交时间
  "ip_address": String,          // IP 地址 (用于匿名追踪)
  "answers": [                   // 答案数组
    {
      "question_id": String,     // 对应 surveys.questions 里的 question_id
      "answer": Mixed            // 根据题目类型而定的灵活数据类型
                                 // - 单选题 (single_choice): String (存 option_id)
                                 // - 多选题 (multiple_choice): Array of Strings (存多个 option_id)
                                 // - 填空题 (text): String (存文本或数字)
                                 // - 评分题 (rating): Number (存数字)
    }
  ],
  "completion_time": Number      // 完成问卷所耗费的秒数
}
```

**索引 (Indexes):**
* `survey_id` + `respondent_id` (复合索引，用于快速检查是否重复提交)
* `survey_id` + `submitted_at` (复合索引，用于按时间进行数据统计)
* `respondent_id`

**设计思路 (Design Rationale):**
* **答案被嵌套在单条答题记录中**，因为它们属于同一次答题提交（不可分割的原子单元），并且总是一起被存取。
* 使用 `question_id` 字符串进行匹配，允许灵活地进行数据聚合查询，而无需进行复杂的跨表查找。
* `answer` 字段使用混合（Mixed）类型，以完美适应单选、多选、填空等不同题目类型的数据格式。

---

### 扩展性考量 (Scalability Considerations)

1. **关注点分离 (Separation of Concerns):** 用户、问卷和答题记录分别放在不同的集合中，允许系统独立地对这三部分进行扩展和查询。
2. **嵌套与引用的权衡 (Embedded vs Referenced):**
   * 题目嵌套在问卷中（紧密耦合，总是一起查询）。
   * 答案嵌套在答题记录中（原子操作单元）。
   * 用户与问卷之间的关联使用 ObjectId 引用（松散耦合，便于未来扩展）。
3. **条件逻辑支持 (Conditional Logic Support):** 题目中的 `logic` 字段通过数据结构配置来支持跳转逻辑，完全避免了硬编码，契合业务需求。
4. **未来扩展方向 (Future Extensions):**
   * 可新增 `survey_templates` 集合用于存储可复用的问卷模板。
   * 可新增 `analytics` 集合用于存储定时计算好的统计缓存数据。
   * 可以在 `surveys` 中增加 `collaborators` 数组，以支持多用户协同编辑问卷。
   * 可以在 `surveys` 中增加 `tags` 数组用于问卷分类。
5. **性能优化 (Performance):**
   * 复合索引有效支持了高频的查询模式（如查重和统计）。
   * 嵌套文档极大地减少了数据库的查询次数（Query Count）。
   * MongoDB 灵活的 Schema 允许在不进行数据迁移的情况下随时增加新字段。
