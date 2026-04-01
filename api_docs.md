# API 接口文档

本文档以 `db_design.md` 为准，适用于 FastAPI + MongoDB 项目联调。

## 1. 接口清单

| 模块 | 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|------|
| 认证 | POST | `/auth/register` | 无 | 用户注册 |
| 认证 | POST | `/auth/login` | 无 | 用户登录 |
| 问卷管理 | POST | `/surveys` | 需要 JWT | 创建问卷 |
| 问卷管理 | GET | `/surveys/my` | 需要 JWT | 获取我的问卷列表 |
| 问卷管理 | GET | `/surveys/{survey_id}` | 需要 JWT | 获取问卷详情（创建者） |
| 问卷管理 | PUT | `/surveys/{survey_id}` | 需要 JWT | 编辑问卷（创建者） |
| 问卷管理 | POST | `/surveys/{survey_id}/publish` | 需要 JWT | 发布问卷 |
| 问卷管理 | POST | `/surveys/{survey_id}/close` | 需要 JWT | 关闭问卷 |
| 问卷管理 | DELETE | `/surveys/{survey_id}` | 需要 JWT | 删除问卷 |
| 填写 | GET | `/public/surveys/{access_code}` | 无 | 通过访问码获取可填写问卷 |
| 填写 | POST | `/responses` | 条件鉴权 | 提交答卷 |
| 统计 | GET | `/surveys/{survey_id}/statistics` | 需要 JWT | 获取问卷整体统计 |
| 统计 | GET | `/surveys/{survey_id}/questions/{question_id}/statistics` | 需要 JWT | 获取单题统计 |

## 2. 统一约定

### 2.1 基础约定

- 协议：HTTP + JSON
- 请求头：`Content-Type: application/json`
- 鉴权头：`Authorization: Bearer <token>`
- 时间格式：ISO 8601（UTC），例如 `2026-12-31T23:59:59Z`
- ID 类型：字符串（后端内部映射 MongoDB `ObjectId`）
- `access_code`：问卷公开访问码，用于生成分享链接和公开填写入口（如 `/public/surveys/ABC123`）

### 2.2 统一响应格式

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

错误响应：

```json
{
  "code": 400,
  "message": "错误描述信息",
  "data": null
}
```

### 2.3 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 失效 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 2.4 鉴权与访问控制规则

- `POST /responses` 条件鉴权规则：
  - `survey.settings.allow_anonymous = true`：可匿名提交（可不带 token）
  - `survey.settings.allow_anonymous = false`：必须登录提交（必须带 token）
- 问卷创建/编辑/发布/关闭/删除/统计仅创建者可操作。
- 仅 `status = published` 的问卷可通过公开访问码获取/提交答卷。
- `deadline` 已过期时，拒绝新答卷提交。
- `allow_multiple = false` 时，同一登录用户不可重复提交。

### 2.5 问卷状态与编辑规则

- 状态枚举：`draft | published | closed`
- 默认：创建后为 `draft`
- 发布：`draft/closed -> published`
- 关闭：`published -> closed`
- 编辑题目结构：仅允许 `draft` 或 `closed` 状态
- 若问卷已发布且 `response_count > 0`，关闭后仍不允许修改 `questions` 结构（可修改标题、描述、截止时间、设置）

## 3. 用户认证接口

### 3.1 用户注册

**接口**：`POST /auth/register`

**请求体结构**：

```json
{
  "username": "string",
  "password": "string",
  "email": "string"
}
```

字段约束：

- `username`：2-50 字符，唯一
- `password`：6-128 字符
- `email`：合法邮箱格式，唯一

**成功响应 data 结构**：

```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "username": "testuser",
  "email": "test@example.com",
  "created_at": "2026-04-01T00:00:00Z"
}
```

### 3.2 用户登录

**接口**：`POST /auth/login`

**请求体结构**：

```json
{
  "username": "string",
  "password": "string"
}
```

**成功响应 data 结构**：

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "user_id": "507f1f77bcf86cd799439011",
    "username": "testuser",
    "email": "test@example.com",
    "created_at": "2026-04-01T00:00:00Z"
  }
}
```

## 4. 问卷管理接口

### 4.1 创建问卷

**接口**：`POST /surveys`

**请求体结构**：

```json
{
  "title": "string",
  "description": "string",
  "settings": {
    "allow_anonymous": true,
    "allow_multiple": false
  },
  "deadline": "2026-12-31T23:59:59Z"
}
```

**成功响应 data 结构**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "status": "draft",
  "access_code": "ABC123",
  "created_at": "2026-04-01T00:00:00Z"
}
```

### 4.2 获取用户创建的问卷列表

**接口**：`GET /surveys/my`

**查询参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | Number | 否 | 1 | 页码 |
| `page_size` | Number | 否 | 10 | 每页数量 |

**请求体**：无

**响应 data 结构**：

```json
{
  "total": 25,
  "page": 1,
  "page_size": 10,
  "surveys": [
    {
      "survey_id": "507f1f77bcf86cd799439012",
      "title": "用户满意度调查",
      "description": "请填写您的真实感受",
      "status": "published",
      "access_code": "ABC123",
      "response_count": 42,
      "created_at": "2026-04-01T00:00:00Z",
      "deadline": "2026-12-31T23:59:59Z"
    }
  ]
}
```

### 4.3 获取问卷详情

**接口**：`GET /surveys/{survey_id}`

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `survey_id` | String | 问卷 ID |

**请求体**：无

**响应 data 结构**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "title": "用户满意度调查",
  "description": "请填写您的真实感受",
  "status": "published",
  "access_code": "ABC123",
  "settings": {
    "allow_anonymous": true,
    "allow_multiple": false
  },
  "deadline": "2026-12-31T23:59:59Z",
  "creator_id": "507f1f77bcf86cd799439011",
  "created_at": "2026-04-01T00:00:00Z",
  "updated_at": "2026-04-01T00:00:00Z",
  "response_count": 42,
  "questions": [
    {
      "question_id": "q1",
      "type": "single_choice",
      "title": "您对我们的服务满意吗？",
      "required": true,
      "order": 1,
      "options": [
        {"option_id": "opt1", "text": "非常满意"},
        {"option_id": "opt2", "text": "满意"},
        {"option_id": "opt3", "text": "一般"},
        {"option_id": "opt4", "text": "不满意"}
      ],
      "validation": {},
      "logic": {
        "enabled": true,
        "rules": [
          {
            "condition": {
              "type": "select_option",
              "option_id": "opt4"
            },
            "action": {
              "type": "jump_to",
              "target_question_id": "q4"
            }
          }
        ]
      }
    },
    {
      "question_id": "q2",
      "type": "multiple_choice",
      "title": "您使用过哪些功能？（至少选1项，最多选3项）",
      "required": true,
      "order": 2,
      "options": [
        {"option_id": "opt1", "text": "功能A"},
        {"option_id": "opt2", "text": "功能B"},
        {"option_id": "opt3", "text": "功能C"},
        {"option_id": "opt4", "text": "功能D"}
      ],
      "validation": {
        "min_selected": 1,
        "max_selected": 3
      },
      "logic": {
        "enabled": true,
        "rules": [
          {
            "condition": {
              "type": "contains_option",
              "option_ids": ["opt1", "opt2"],
              "match_type": "all"
            },
            "action": {
              "type": "jump_to",
              "target_question_id": "q4"
            }
          }
        ]
      }
    },
    {
      "question_id": "q3",
      "type": "text_input",
      "title": "请简要描述您的建议",
      "required": false,
      "order": 3,
      "options": [],
      "validation": {
        "min_length": 10,
        "max_length": 500
      },
      "logic": {
        "enabled": false,
        "rules": []
      }
    },
    {
      "question_id": "q4",
      "type": "number_input",
      "title": "您的年龄",
      "required": true,
      "order": 4,
      "options": [],
      "validation": {
        "min_value": 1,
        "max_value": 150,
        "integer_only": true
      },
      "logic": {
        "enabled": true,
        "rules": [
          {
            "condition": {
              "type": "number_compare",
              "operator": "lt",
              "value": 18
            },
            "action": {
              "type": "end_survey"
            }
          },
          {
            "condition": {
              "type": "number_compare",
              "operator": "between",
              "min_value": 18,
              "max_value": 25
            },
            "action": {
              "type": "jump_to",
              "target_question_id": "q6"
            }
          }
        ]
      }
    }
  ]
}
```

### 4.4 编辑问卷

**接口**：`PUT /surveys/{survey_id}`

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `survey_id` | String | 问卷 ID |

**请求体结构**：

```json
{
  "title": "string",
  "description": "string",
  "settings": {
    "allow_anonymous": true,
    "allow_multiple": false
  },
  "deadline": "2026-12-31T23:59:59Z",
  "questions": [
    {
      "question_id": "q1",
      "type": "single_choice",
      "title": "问题标题",
      "required": true,
      "order": 1,
      "options": [
        {"option_id": "opt1", "text": "选项1"},
        {"option_id": "opt2", "text": "选项2"}
      ],
      "validation": {},
      "logic": {
        "enabled": false,
        "rules": []
      }
    }
  ]
}
```

说明：

- `draft/closed` 且 `response_count = 0` 时允许修改 `questions`。
- 若已有提交记录（`response_count > 0`），不允许修改 `questions`，仅允许更新非结构字段。

**成功响应 data 结构**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "updated_at": "2026-04-01T01:00:00Z"
}
```

### 4.5 发布问卷

**接口**：`POST /surveys/{survey_id}/publish`

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `survey_id` | String | 问卷 ID |

**请求体**：无

**成功响应 data 结构**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "status": "published",
  "access_code": "ABC123",
  "share_url": "http://localhost:3000/survey/ABC123"
}
```

### 4.6 关闭问卷

**接口**：`POST /surveys/{survey_id}/close`

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `survey_id` | String | 问卷 ID |

**请求体**：无

**成功响应 data 结构**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "status": "closed",
  "updated_at": "2026-04-01T01:20:00Z"
}
```

### 4.7 删除问卷

**接口**：`DELETE /surveys/{survey_id}`

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `survey_id` | String | 问卷 ID |

**请求体**：无

**成功响应 data 结构**：`null`

## 5. 问卷填写接口

### 5.1 通过访问码获取公开问卷

**接口**：`GET /public/surveys/{access_code}`

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `access_code` | String | 问卷公开访问码 |

**请求体**：无

说明：

- 仅返回填写端需要的问卷信息，不返回创建者后台敏感信息。
- 仅当问卷已发布且未关闭时可获取。

**成功响应 data 结构**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "title": "用户满意度调查",
  "description": "请填写您的真实感受",
  "access_code": "ABC123",
  "settings": {
    "allow_anonymous": true,
    "allow_multiple": false
  },
  "deadline": "2026-12-31T23:59:59Z",
  "questions": [
    {
      "question_id": "q1",
      "type": "single_choice",
      "title": "您对我们的服务满意吗？",
      "required": true,
      "order": 1,
      "options": [
        {"option_id": "opt1", "text": "非常满意"},
        {"option_id": "opt2", "text": "满意"},
        {"option_id": "opt3", "text": "一般"},
        {"option_id": "opt4", "text": "不满意"}
      ],
      "validation": {},
      "logic": {
        "enabled": true,
        "rules": [
          {
            "condition": {"type": "select_option", "option_id": "opt4"},
            "action": {"type": "jump_to", "target_question_id": "q4"}
          }
        ]
      }
    },
    {
      "question_id": "q2",
      "type": "multiple_choice",
      "title": "您使用过哪些功能？",
      "required": true,
      "order": 2,
      "options": [
        {"option_id": "opt1", "text": "功能A"},
        {"option_id": "opt2", "text": "功能B"}
      ],
      "validation": {"min_selected": 1, "max_selected": 2},
      "logic": {"enabled": false, "rules": []}
    },
    {
      "question_id": "q3",
      "type": "text_input",
      "title": "请简要描述您的建议",
      "required": false,
      "order": 3,
      "options": [],
      "validation": {"min_length": 10, "max_length": 500},
      "logic": {"enabled": false, "rules": []}
    },
    {
      "question_id": "q4",
      "type": "number_input",
      "title": "您的年龄",
      "required": true,
      "order": 4,
      "options": [],
      "validation": {"min_value": 1, "max_value": 150, "integer_only": true},
      "logic": {"enabled": false, "rules": []}
    }
  ]
}
```

### 5.2 提交答卷

**接口**：`POST /responses`

**请求体结构**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "access_code": "ABC123",
  "answers": [
    {
      "question_id": "q1",
      "answer": "opt1"
    },
    {
      "question_id": "q2",
      "answer": ["opt1", "opt3"]
    },
    {
      "question_id": "q3",
      "answer": "这是我的文本回答"
    },
    {
      "question_id": "q4",
      "answer": 85
    }
  ],
  "completion_time": 120
}
```

**成功响应 data 结构**：

```json
{
  "response_id": "507f1f77bcf86cd799439013",
  "survey_id": "507f1f77bcf86cd799439012",
  "submitted_at": "2026-04-01T02:00:00Z"
}
```

## 6. 统计分析接口

### 6.1 获取问卷整体统计

**接口**：`GET /surveys/{survey_id}/statistics`

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `survey_id` | String | 问卷 ID |

**请求体**：无

**响应 data 结构**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "survey_title": "用户满意度调查",
  "total_responses": 150,
  "question_statistics": [
    {
      "question_id": "q1",
      "title": "您对我们的服务满意吗？",
      "type": "single_choice",
      "total_answers": 150,
      "option_statistics": [
        {"option_id": "opt1", "text": "非常满意", "count": 80, "percentage": 53.33},
        {"option_id": "opt2", "text": "满意", "count": 50, "percentage": 33.33},
        {"option_id": "opt3", "text": "一般", "count": 15, "percentage": 10.0},
        {"option_id": "opt4", "text": "不满意", "count": 5, "percentage": 3.33}
      ]
    },
    {
      "question_id": "q2",
      "title": "您使用过哪些功能？",
      "type": "multiple_choice",
      "total_answers": 150,
      "option_statistics": [
        {"option_id": "opt1", "text": "功能A", "count": 120, "percentage": 80.0},
        {"option_id": "opt2", "text": "功能B", "count": 90, "percentage": 60.0}
      ]
    },
    {
      "question_id": "q3",
      "title": "请简要描述您的建议",
      "type": "text_input",
      "total_answers": 130,
      "text_responses": [
        "建议增加更多功能",
        "界面很好用",
        "希望优化性能"
      ]
    },
    {
      "question_id": "q4",
      "title": "您的年龄",
      "type": "number_input",
      "total_answers": 150,
      "number_statistics": {
        "average": 28.5,
        "min": 18,
        "max": 55,
        "values": [25, 30, 28, 35, 22]
      }
    }
  ]
}
```

### 6.2 获取单个题目统计

**接口**：`GET /surveys/{survey_id}/questions/{question_id}/statistics`

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `survey_id` | String | 问卷 ID |
| `question_id` | String | 题目 ID |

**请求体**：无

**成功响应 data 结构**：

按题型不同，返回结构有所区别：

**单选题 / 多选题**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "question_id": "q1",
  "title": "您对我们的服务满意吗？",
  "type": "single_choice",
  "total_answers": 150,
  "option_statistics": [
    {"option_id": "opt1", "text": "非常满意", "count": 80, "percentage": 53.33},
    {"option_id": "opt2", "text": "满意", "count": 50, "percentage": 33.33}
  ]
}
```

**文本填空题**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "question_id": "q3",
  "title": "请简要描述您的建议",
  "type": "text_input",
  "total_answers": 130,
  "text_responses": [
    "建议增加更多功能",
    "界面很好用",
    "希望优化性能"
  ]
}
```

**数字填空题**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "question_id": "q4",
  "title": "您的年龄",
  "type": "number_input",
  "total_answers": 150,
  "number_statistics": {
    "average": 28.5,
    "min": 18,
    "max": 55,
    "values": [25, 30, 28, 35, 22]
  }
}
```

## 7. 题目类型与数据结构参考

本节补充说明四种题型的完整字段结构，供前后端联调参考

### 7.1 题目通用结构

```json
{
  "question_id": "string",     // 题目唯一标识，如 "q1"
  "type": "string",            // 题型：single_choice / multiple_choice / text_input / number_input
  "title": "string",           // 题目文本
  "required": true,            // 是否必答
  "order": 1,                  // 显示顺序
  "options": [],               // 选项数组（仅选择题使用，填空题传空数组）
  "validation": {},            // 校验规则（按题型不同，字段不同）
  "logic": {                   // 跳转逻辑
    "enabled": false,
    "rules": []
  }
}
```

### 7.2 各题型 validation 字段

**单选题 (single_choice)**：无特殊校验字段，`validation` 传 `{}`。

**多选题 (multiple_choice)**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `min_selected` | Number | 最少选择数量 |
| `max_selected` | Number | 最多选择数量 |
| `exact_selected` | Number | 必须选择的精确数量（优先级高于 min/max） |

**文本填空 (text_input)**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `min_length` | Number | 最少字数 |
| `max_length` | Number | 最多字数 |

**数字填空 (number_input)**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `min_value` | Number | 最小值 |
| `max_value` | Number | 最大值 |
| `integer_only` | Boolean | 是否必须为整数 |

### 7.3 跳转逻辑结构

```json
{
  "logic": {
    "enabled": true,
    "rules": [
      {
        "condition": { ... },
        "action": { ... }
      }
    ]
  }
}
```

**三种条件类型 (condition.type)**：

**`select_option`** — 单选匹配（适用于 single_choice）：

```json
{
  "type": "select_option",
  "option_id": "opt4"
}
```

**`contains_option`** — 多选包含（适用于 multiple_choice）：

```json
{
  "type": "contains_option",
  "option_ids": ["opt1", "opt2"],
  "match_type": "any"
}
```

`match_type`：`"any"` 表示选中任一即触发（OR），`"all"` 表示全部选中才触发（AND）。

**`number_compare`** — 数字比较（适用于 number_input）：

```json
{
  "type": "number_compare",
  "operator": "between",
  "min_value": 18,
  "max_value": 25
}
```

`operator` 可选值：`eq` / `ne` / `gt` / `gte` / `lt` / `lte` / `between`。使用 `between` 时需提供 `min_value` + `max_value`，其余使用 `value` 字段。

**两种动作类型 (action.type)**：

```json
// 跳转到指定题目
{"type": "jump_to", "target_question_id": "q5"}

// 直接结束问卷
{"type": "end_survey"}
```

### 7.4 各题型答案格式（提交答卷时）

| 题型 | answer 类型 | 示例 |
|------|-------------|------|
| `single_choice` | String（选中的 option_id） | `"opt1"` |
| `multiple_choice` | [String]（选中的 option_id 数组） | `["opt1", "opt3"]` |
| `text_input` | String（文本内容） | `"这是我的回答"` |
| `number_input` | Number（数字值） | `85` |

### 7.5 各题型统计返回格式

**单选题 / 多选题**：返回 `option_statistics` 数组，每个选项包含 `count` 和 `percentage`。多选题的 `percentage` 基于总答题人数计算（可超过 100%）。

**文本填空**：返回 `text_responses` 字符串数组，包含所有填写内容。

**数字填空**：返回 `number_statistics` 对象，包含 `average`、`min`、`max`、`values`。

## 8. 错误码说明

| 错误码 | 说明 |
|--------|------|
| 1001 | 用户名已存在 |
| 1002 | 用户名或密码错误 |
| 1003 | Token 无效或已过期 |
| 2001 | 问卷不存在 |
| 2002 | 无权限操作该问卷 |
| 2003 | 问卷已关闭 |
| 2004 | 问卷已过期 |
| 2005 | 访问码无效 |
| 3001 | 答案校验失败 |
| 3002 | 不允许重复提交 |
| 3003 | 必填题未回答 |
