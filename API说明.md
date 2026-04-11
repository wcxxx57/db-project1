# API 接口文档（第二阶段）

本文档覆盖第一阶段全部接口及第二阶段新增接口，适用于 FastAPI + MongoDB 项目联调。

## 1. 接口清单

### 1.1 第一阶段接口

| 模块     | 方法   | 路径                                                      | 鉴权     | 说明                       |
| -------- | ------ | --------------------------------------------------------- | -------- | -------------------------- |
| 认证     | POST   | `/auth/register`                                          | 无       | 用户注册                   |
| 认证     | POST   | `/auth/login`                                             | 无       | 用户登录                   |
| 问卷管理 | POST   | `/surveys`                                                | 需要 JWT | 创建问卷                   |
| 问卷管理 | GET    | `/surveys/my`                                             | 需要 JWT | 获取我的问卷列表           |
| 问卷管理 | GET    | `/surveys/{survey_id}`                                    | 需要 JWT | 获取问卷详情（创建者）     |
| 问卷管理 | PUT    | `/surveys/{survey_id}`                                    | 需要 JWT | 编辑问卷（第二阶段改为引用格式） |
| 问卷管理 | POST   | `/surveys/{survey_id}/publish`                            | 需要 JWT | 发布问卷                   |
| 问卷管理 | POST   | `/surveys/{survey_id}/close`                              | 需要 JWT | 关闭问卷                   |
| 问卷管理 | DELETE | `/surveys/{survey_id}`                                    | 需要 JWT | 删除问卷                   |
| 填写     | GET    | `/public/surveys/{access_code}`                           | 可选     | 通过访问码获取可填写问卷   |
| 填写     | POST   | `/responses`                                              | 需要 JWT | 提交答卷                   |
| 答卷管理 | GET    | `/surveys/{survey_id}/responses`                          | 需要 JWT | 获取问卷的所有答卷列表     |
| 答卷管理 | GET    | `/responses/{response_id}`                                | 需要 JWT | 获取答卷详情               |
| 统计     | GET    | `/surveys/{survey_id}/statistics`                         | 需要 JWT | 获取问卷整体统计           |
| 统计     | GET    | `/surveys/{survey_id}/questions/{question_id}/statistics` | 需要 JWT | 获取单题统计               |

### 1.2 第二阶段新增接口

| 模块     | 方法   | 路径                                                          | 鉴权     | 说明             |
| -------- | ------ | ------------------------------------------------------------- | -------- | ---------------- |
| 题目管理 | POST   | `/questions`                                                  | 需要 JWT | 创建题目         |
| 题目管理 | GET    | `/questions/my`                                               | 需要 JWT | 获取我创建的题目 |
| 题目管理 | GET    | `/questions/shared`                                           | 需要 JWT | 获取共享给我的题目 |
| 题目管理 | GET    | `/questions/bank`                                             | 需要 JWT | 获取我的题库     |
| 题目管理 | GET    | `/questions/{question_id}`                                    | 需要 JWT | 获取题目详情     |
| 版本管理 | POST   | `/questions/{question_id}/versions`                           | 需要 JWT | 创建新版本       |
| 版本管理 | GET    | `/questions/{question_id}/versions`                           | 需要 JWT | 获取版本历史     |
| 版本管理 | POST   | `/questions/{question_id}/versions/{version_number}/restore`  | 需要 JWT | 恢复历史版本     |
| 共享管理 | POST   | `/questions/{question_id}/share`                              | 需要 JWT | 共享题目         |
| 共享管理 | POST   | `/questions/{question_id}/unshare`                            | 需要 JWT | 取消共享         |
| 题库管理 | POST   | `/questions/{question_id}/bank`                               | 需要 JWT | 加入题库         |
| 题库管理 | DELETE | `/questions/{question_id}/bank`                               | 需要 JWT | 移出题库         |
| 题目管理 | GET    | `/questions/{question_id}/usage`                              | 需要 JWT | 查看题目使用情况 |
| 题目管理 | DELETE | `/questions/{question_id}`                                    | 需要 JWT | 删除题目         |
| 统计     | GET    | `/questions/{question_ref_id}/cross-statistics`               | 需要 JWT | 跨问卷单题统计   |

## 2. 统一约定

### 2.1 基础约定

- 协议：HTTP + JSON
- 请求头：`Content-Type: application/json`
- 鉴权头：`Authorization: Bearer <token>`
- 时间格式：ISO 8601（UTC），例如 `2026-12-31T23:59:59Z`
- ID 类型：字符串（后端内部映射 MongoDB `ObjectId`）
- `access_code`：问卷公开访问码，用于生成分享链接和公开填写入口
- `question_id`（题目谱系 ID）：独立题目的全局唯一标识，即 MongoDB `ObjectId`
- `question_id`（问卷内局部题号）：问卷内部的题目编号，如 `q1`、`q2`，用于跳转逻辑路由

### 2.2 统一响应格式

- HTTP 状态码通过响应状态行表达（如 200/400/401/403/404）。
- 响应体中的 `code` 为业务码：成功固定为 `0`，失败使用业务错误码（如 1001/2001/4001）。

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

错误响应：

```json
{
  "code": 4001,
  "message": "错误描述信息",
  "data": null
}
```

### 2.3 HTTP 状态码

| 状态码 | 说明                                         |
| ------ | -------------------------------------------- |
| 200    | 请求成功                                     |
| 400    | 请求参数错误                                 |
| 401    | 未认证或 Token 失效                          |
| 403    | 无权限访问                                   |
| 404    | 资源不存在                                   |
| 422    | 请求体或参数格式校验失败（FastAPI 默认行为） |
| 500    | 服务器内部错误                               |

### 2.4 鉴权与访问控制规则

- `POST /responses` 必须登录（必须携带 JWT Token），即填写问卷也要求是注册用户。
  - `survey.settings.allow_anonymous = true`：允许前端表单中选择匿名提交 `is_anonymous: true`，提交后系统统计将隐去答题者真实身份。
  - `survey.settings.allow_anonymous = false`：提交时将强制记录答题者真实身份并参与系统统计展示。
- 问卷创建/编辑/发布/关闭/删除/统计仅创建者可操作。
- 仅 `status = published` 的问卷可通过公开访问码获取/提交答卷。
- `deadline` 已过期时，拒绝新答卷提交。
- `allow_multiple = false` 时：同一 `survey_id + respondent_id` 不可重复提交，返回 3002 错误码。
- `allow_multiple = true` 时，允许重复提交，系统分别记录。
- 题目的访问权限：创建者和被共享者均可访问。
- 题目的共享/取消共享/删除操作仅创建者可执行。
- 题库操作（加入/移出）：创建者和被共享者均可执行。

### 2.5 问卷状态与编辑规则

- 状态枚举：`draft | published | closed`
- 默认：创建后为 `draft`
- 发布：`draft/closed -> published`
- 关闭：`published -> closed`
- 编辑题目结构：仅允许 `draft` 或 `closed` 状态下编辑，`published` 状态下应先 `closed` 才能修改

---

## 3. 用户认证接口

### 3.1 用户注册

- **方法**：`POST`
- **路径**：`/auth/register`
- **鉴权**：无

**请求体**：

```json
{
  "username": "string",
  "password": "string"
}
```

字段约束：

| 字段       | 类型   | 必填 | 约束         | 说明     |
| ---------- | ------ | ---- | ------------ | -------- |
| `username` | String | 是   | 2-50 字符，唯一 | 用户名   |
| `password` | String | 是   | 8-128 字符   | 密码     |

**成功响应 data**：

```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "username": "testuser",
  "created_at": "2026-04-01T00:00:00Z"
}
```

**可能的错误码**：

| 错误码 | 说明         |
| ------ | ------------ |
| 1001   | 用户名已存在 |

---

### 3.2 用户登录

- **方法**：`POST`
- **路径**：`/auth/login`
- **鉴权**：无

**请求体**：

```json
{
  "username": "string",
  "password": "string"
}
```

**成功响应 data**：

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "user_id": "507f1f77bcf86cd799439011",
    "username": "testuser",
    "created_at": "2026-04-01T00:00:00Z"
  }
}
```

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 1002   | 用户名或密码错误 |

---

## 4. 问卷管理接口

### 4.1 创建问卷

- **方法**：`POST`
- **路径**：`/surveys`
- **鉴权**：需要 JWT

**请求体**：

```json
{
  "title": "用户满意度调查",
  "description": "请填写您的真实感受",
  "settings": {
    "allow_anonymous": true,
    "allow_multiple": false
  },
  "deadline": "2026-12-31T23:59:59Z"
}
```

| 字段          | 类型     | 必填 | 说明                       |
| ------------- | -------- | ---- | -------------------------- |
| `title`       | String   | 是   | 问卷标题（1-200 字符）     |
| `description` | String   | 否   | 问卷说明（最多 2000 字符） |
| `settings`    | Object   | 否   | 问卷设置                   |
| `deadline`    | DateTime | 否   | 截止时间                   |

**成功响应 data**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "status": "draft",
  "access_code": "ABC123",
  "created_at": "2026-04-01T00:00:00Z"
}
```

---

### 4.2 获取我的问卷列表

- **方法**：`GET`
- **路径**：`/surveys/my`
- **鉴权**：需要 JWT

**查询参数**：

| 参数        | 类型   | 必填 | 默认值 | 说明               |
| ----------- | ------ | ---- | ------ | ------------------ |
| `page`      | Number | 否   | 1      | 页码（最小为 1）   |
| `page_size` | Number | 否   | 10     | 每页数量（1-100）  |

**成功响应 data**：

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

---

### 4.3 获取问卷详情

- **方法**：`GET`
- **路径**：`/surveys/{survey_id}`
- **鉴权**：需要 JWT

**路径参数**：

| 参数        | 类型   | 说明    |
| ----------- | ------ | ------- |
| `survey_id` | String | 问卷 ID |

**成功响应 data**：

第二阶段中，`questions` 字段为引用列表格式，每个题目引用包含引用信息和解析后的题目内容。

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
      "order": 1,
      "question_ref_id": "664a1b2c3d4e5f6789012345",
      "version_number": 1,
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
      },
      "type": "single_choice",
      "title": "您对我们的服务满意吗？",
      "required": true,
      "options": [
        { "option_id": "opt1", "text": "非常满意" },
        { "option_id": "opt2", "text": "满意" },
        { "option_id": "opt3", "text": "一般" },
        { "option_id": "opt4", "text": "不满意" }
      ],
      "validation": {}
    }
  ]
}
```

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 2001   | 问卷不存在       |
| 2002   | 无权限操作该问卷 |

---

### 4.4 编辑问卷（第二阶段引用格式）

- **方法**：`PUT`
- **路径**：`/surveys/{survey_id}`
- **鉴权**：需要 JWT

**路径参数**：

| 参数        | 类型   | 说明    |
| ----------- | ------ | ------- |
| `survey_id` | String | 问卷 ID |

**请求体**：

第二阶段中，`questions` 改为引用列表，每个题目通过 `question_ref_id` 和 `version_number` 引用独立题目库中的题目。

```json
{
  "title": "更新后的标题",
  "description": "更新后的描述",
  "settings": {
    "allow_anonymous": true,
    "allow_multiple": false
  },
  "deadline": "2026-12-31T23:59:59Z",
  "questions": [
    {
      "question_id": "q1",
      "order": 1,
      "question_ref_id": "664a1b2c3d4e5f6789012345",
      "version_number": 1,
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
              "target_question_id": "q3"
            }
          }
        ]
      }
    },
    {
      "question_id": "q2",
      "order": 2,
      "question_ref_id": "664a1b2c3d4e5f6789012346",
      "version_number": 2,
      "logic": {
        "enabled": false,
        "rules": []
      }
    }
  ]
}
```

题目引用项字段说明：

| 字段               | 类型   | 必填 | 说明                                         |
| ------------------ | ------ | ---- | -------------------------------------------- |
| `question_id`      | String | 是   | 问卷内局部题号（如 `q1`），用于跳转逻辑路由 |
| `order`            | Number | 是   | 题目在此问卷中的显示顺序                     |
| `question_ref_id`  | String | 是   | 引用的独立题目谱系 ID                        |
| `version_number`   | Number | 是   | 引用的具体版本号                             |
| `logic`            | Object | 否   | 跳转逻辑（只属于该份问卷）                   |

说明：

- 所有字段均为可选，仅更新提供的字段
- `published` 状态的问卷不可编辑，必须先关闭
- `draft` 或 `closed` 状态的问卷可以编辑

**成功响应 data**：与 `GET /surveys/{survey_id}` 结构一致（返回完整的已更新问卷对象）。

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 2001   | 问卷不存在       |
| 2002   | 无权限操作该问卷 |

---

### 4.5 发布问卷

- **方法**：`POST`
- **路径**：`/surveys/{survey_id}/publish`
- **鉴权**：需要 JWT

**路径参数**：

| 参数        | 类型   | 说明    |
| ----------- | ------ | ------- |
| `survey_id` | String | 问卷 ID |

**请求体**：无

**成功响应 data**：与 `GET /surveys/{survey_id}` 结构一致（`status` 变更为 `published`）。

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 2001   | 问卷不存在       |
| 2002   | 无权限操作该问卷 |

---

### 4.6 关闭问卷

- **方法**：`POST`
- **路径**：`/surveys/{survey_id}/close`
- **鉴权**：需要 JWT

**路径参数**：

| 参数        | 类型   | 说明    |
| ----------- | ------ | ------- |
| `survey_id` | String | 问卷 ID |

**请求体**：无

**成功响应 data**：与 `GET /surveys/{survey_id}` 结构一致（`status` 变更为 `closed`）。

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 2001   | 问卷不存在       |
| 2002   | 无权限操作该问卷 |

---

### 4.7 删除问卷

- **方法**：`DELETE`
- **路径**：`/surveys/{survey_id}`
- **鉴权**：需要 JWT

**路径参数**：

| 参数        | 类型   | 说明    |
| ----------- | ------ | ------- |
| `survey_id` | String | 问卷 ID |

**请求体**：无

**成功响应 data**：`null`

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 2001   | 问卷不存在       |
| 2002   | 无权限操作该问卷 |

---

## 5. 问卷填写接口

### 5.1 通过访问码获取公开问卷

- **方法**：`GET`
- **路径**：`/public/surveys/{access_code}`
- **鉴权**：可选（携带 JWT 可用于判断用户是否已提交）

**路径参数**：

| 参数          | 类型   | 说明           |
| ------------- | ------ | -------------- |
| `access_code` | String | 问卷公开访问码 |

说明：

- 仅返回填写端需要的问卷信息，不返回创建者后台敏感信息
- 仅当问卷已发布且未关闭时可获取

**成功响应 data**：

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
        { "option_id": "opt1", "text": "非常满意" },
        { "option_id": "opt2", "text": "满意" }
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

**可能的错误码**：

| 错误码 | 说明       |
| ------ | ---------- |
| 2003   | 问卷已关闭 |
| 2005   | 访问码无效 |

---

### 5.2 提交答卷

- **方法**：`POST`
- **路径**：`/responses`
- **鉴权**：需要 JWT

**请求体**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "access_code": "ABC123",
  "is_anonymous": true,
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

| 字段              | 类型    | 必填 | 说明                         |
| ----------------- | ------- | ---- | ---------------------------- |
| `survey_id`       | String  | 是   | 问卷 ID                     |
| `access_code`     | String  | 是   | 问卷访问码                   |
| `is_anonymous`    | Boolean | 否   | 是否匿名提交                 |
| `answers`         | Array   | 是   | 答案列表                     |
| `completion_time` | Number  | 否   | 完成用时（秒）               |

各题型答案格式：

| 题型              | answer 类型                       | 示例               |
| ----------------- | --------------------------------- | ------------------ |
| `single_choice`   | String（选中的 option_id）        | `"opt1"`           |
| `multiple_choice` | [String]（选中的 option_id 数组） | `["opt1", "opt3"]` |
| `text_input`      | String（文本内容）                | `"这是我的回答"`   |
| `number_input`    | Number（数字值）                  | `85`               |

**成功响应 data**：

```json
{
  "response_id": "507f1f77bcf86cd799439013",
  "survey_id": "507f1f77bcf86cd799439012",
  "submitted_at": "2026-04-01T02:00:00Z",
  "submission_count": 1
}
```

**可能的错误码**：

| 错误码 | 说明           |
| ------ | -------------- |
| 2001   | 问卷不存在     |
| 2003   | 问卷已关闭     |
| 2004   | 问卷已过期     |
| 2005   | 访问码无效     |
| 3001   | 答案校验失败   |
| 3002   | 不允许重复提交 |
| 3003   | 必填题未回答   |
| 3004   | 需要登录       |

---

### 5.3 获取答卷列表（创建者使用）

- **方法**：`GET`
- **路径**：`/surveys/{survey_id}/responses`
- **鉴权**：需要 JWT

**路径参数**：

| 参数        | 类型   | 说明    |
| ----------- | ------ | ------- |
| `survey_id` | String | 问卷 ID |

**请求体**：无

**成功响应 data**：答卷列表数组。

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 2001   | 问卷不存在       |
| 2002   | 无权限操作该问卷 |

---

### 5.4 获取答卷详情（创建者使用）

- **方法**：`GET`
- **路径**：`/responses/{response_id}`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明    |
| ------------- | ------ | ------- |
| `response_id` | String | 答卷 ID |

**请求体**：无

**成功响应 data**：答卷详情对象。

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 2002   | 无权限操作       |

---

## 6. 统计分析接口

### 6.1 获取问卷整体统计

- **方法**：`GET`
- **路径**：`/surveys/{survey_id}/statistics`
- **鉴权**：需要 JWT

**路径参数**：

| 参数        | 类型   | 说明    |
| ----------- | ------ | ------- |
| `survey_id` | String | 问卷 ID |

**请求体**：无

**成功响应 data**：

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
        {
          "option_id": "opt1",
          "text": "非常满意",
          "count": 80,
          "percentage": 53.33,
          "respondents": [
            {
              "respondent_id": "507f1f77bcf86cd799439011",
              "display_name": "testuser",
              "is_anonymous": false
            },
            {
              "respondent_id": null,
              "display_name": "匿名用户",
              "is_anonymous": true
            }
          ]
        }
      ]
    },
    {
      "question_id": "q3",
      "title": "请简要描述您的建议",
      "type": "text_input",
      "total_answers": 130,
      "text_responses": ["建议增加更多功能", "界面很好用"]
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

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 2001   | 问卷不存在       |
| 2002   | 无权限查看统计   |

---

### 6.2 获取单个题目统计

- **方法**：`GET`
- **路径**：`/surveys/{survey_id}/questions/{question_id}/statistics`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明                      |
| ------------- | ------ | ------------------------- |
| `survey_id`   | String | 问卷 ID                   |
| `question_id` | String | 问卷内局部题号（如 `q1`） |

**请求体**：无

**成功响应 data**：

按题型不同返回不同结构，与问卷整体统计中的 `question_statistics` 单个元素结构一致，额外包含 `survey_id` 字段。

**单选题 / 多选题**：

```json
{
  "survey_id": "507f1f77bcf86cd799439012",
  "question_id": "q1",
  "title": "您对我们的服务满意吗？",
  "type": "single_choice",
  "total_answers": 150,
  "option_statistics": [
    {
      "option_id": "opt1",
      "text": "非常满意",
      "count": 80,
      "percentage": 53.33,
      "respondents": [...]
    }
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
  "text_responses": ["建议增加更多功能", "界面很好用"]
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

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 2001   | 问卷或题目不存在 |
| 2002   | 无权限查看统计   |

---

### 6.3 跨问卷单题统计（第二阶段新增）

- **方法**：`GET`
- **路径**：`/questions/{question_ref_id}/cross-statistics`
- **鉴权**：需要 JWT

**路径参数**：

| 参数               | 类型   | 说明               |
| ------------------ | ------ | ------------------ |
| `question_ref_id`  | String | 题目谱系 ID        |

**请求体**：无

说明：

- 按题目谱系聚合所有引用了该题目的问卷答卷数据
- 按 `version_number` 分组展示统计结果
- 创建者和被共享者均可查看

**成功响应 data**：

```json
{
  "question_ref_id": "664a1b2c3d4e5f6789012345",
  "question_title": "您对我们的服务满意吗？",
  "question_type": "single_choice",
  "total_answers": 300,
  "survey_count": 3,
  "surveys": [
    {
      "survey_id": "507f1f77bcf86cd799439012",
      "title": "用户满意度调查 A",
      "status": "published"
    },
    {
      "survey_id": "507f1f77bcf86cd799439013",
      "title": "用户满意度调查 B",
      "status": "closed"
    }
  ],
  "version_statistics": [
    {
      "version_number": 1,
      "title": "您对我们的服务满意吗？",
      "type": "single_choice",
      "total_answers": 200,
      "survey_count": 2,
      "option_statistics": [
        {
          "option_id": "opt1",
          "text": "非常满意",
          "count": 120,
          "percentage": 60.0
        },
        {
          "option_id": "opt2",
          "text": "满意",
          "count": 80,
          "percentage": 40.0
        }
      ]
    },
    {
      "version_number": 2,
      "title": "您对我们的服务满意吗？（修订版）",
      "type": "single_choice",
      "total_answers": 100,
      "survey_count": 1,
      "option_statistics": [
        {
          "option_id": "opt1",
          "text": "非常满意",
          "count": 70,
          "percentage": 70.0
        }
      ]
    }
  ]
}
```

版本统计中按题型不同，包含不同字段：
- 单选题/多选题：`option_statistics` 数组
- 文本填空题：`text_responses` 字符串数组
- 数字填空题：`number_statistics` 对象（含 `average`、`min`、`max`、`values`）

**可能的错误码**：

| 错误码 | 说明               |
| ------ | ------------------ |
| 4001   | 题目不存在         |
| 2002   | 无权限查看该题目统计 |

---

## 7. 题目管理接口（第二阶段新增）

### 7.1 创建题目

- **方法**：`POST`
- **路径**：`/questions`
- **鉴权**：需要 JWT

**请求体**：

```json
{
  "type": "single_choice",
  "title": "您对我们的服务满意吗？",
  "required": true,
  "options": [
    { "option_id": "opt1", "text": "非常满意" },
    { "option_id": "opt2", "text": "满意" },
    { "option_id": "opt3", "text": "一般" },
    { "option_id": "opt4", "text": "不满意" }
  ],
  "validation": {}
}
```

| 字段         | 类型    | 必填 | 说明                                                              |
| ------------ | ------- | ---- | ----------------------------------------------------------------- |
| `type`       | String  | 是   | 题目类型：`single_choice` / `multiple_choice` / `text_input` / `number_input` |
| `title`      | String  | 是   | 题目文本（1-500 字符）                                            |
| `required`   | Boolean | 否   | 是否必答，默认 `true`                                             |
| `options`    | Array   | 否   | 选项列表（仅选择题使用）                                          |
| `validation` | Object  | 否   | 校验规则                                                          |

创建成功后自动生成版本 v1。

**成功响应 data**：

```json
{
  "question_id": "664a1b2c3d4e5f6789012345",
  "version_number": 1,
  "created_at": "2026-04-01T00:00:00Z"
}
```

---

### 7.2 获取我创建的题目

- **方法**：`GET`
- **路径**：`/questions/my`
- **鉴权**：需要 JWT

**请求体**：无

**成功响应 data**：

```json
[
  {
    "question_id": "664a1b2c3d4e5f6789012345",
    "latest_version_number": 3,
    "creator": "507f1f77bcf86cd799439011",
    "latest_title": "您对我们的服务满意吗？",
    "latest_type": "single_choice",
    "created_at": "2026-04-01T00:00:00Z"
  }
]
```

---

### 7.3 获取共享给我的题目

- **方法**：`GET`
- **路径**：`/questions/shared`
- **鉴权**：需要 JWT

**请求体**：无

**成功响应 data**：与 `GET /questions/my` 结构一致。

---

### 7.4 获取我的题库

- **方法**：`GET`
- **路径**：`/questions/bank`
- **鉴权**：需要 JWT

**请求体**：无

**成功响应 data**：与 `GET /questions/my` 结构一致。

---

### 7.5 获取题目详情

- **方法**：`GET`
- **路径**：`/questions/{question_id}`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明         |
| ------------- | ------ | ------------ |
| `question_id` | String | 题目谱系 ID  |

**请求体**：无

**成功响应 data**：

```json
{
  "question_id": "664a1b2c3d4e5f6789012345",
  "latest_version_number": 3,
  "creator": "507f1f77bcf86cd799439011",
  "shared_with": ["507f1f77bcf86cd799439099"],
  "banked_by": ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439099"],
  "versions": [
    {
      "version_number": 1,
      "created_at": "2026-04-01T00:00:00Z",
      "updated_by": "507f1f77bcf86cd799439011",
      "parent_version_number": null,
      "type": "single_choice",
      "title": "您对我们的服务满意吗？",
      "required": true,
      "options": [
        { "option_id": "opt1", "text": "非常满意" },
        { "option_id": "opt2", "text": "满意" }
      ],
      "validation": null
    },
    {
      "version_number": 2,
      "created_at": "2026-04-02T00:00:00Z",
      "updated_by": "507f1f77bcf86cd799439011",
      "parent_version_number": 1,
      "type": "single_choice",
      "title": "您对我们的服务满意吗？（修订版）",
      "required": true,
      "options": [
        { "option_id": "opt1", "text": "非常满意" },
        { "option_id": "opt2", "text": "满意" },
        { "option_id": "opt3", "text": "不满意" }
      ],
      "validation": null
    }
  ]
}
```

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 4001   | 题目不存在       |
| 2002   | 无权限操作该题目 |

---

### 7.6 创建新版本

- **方法**：`POST`
- **路径**：`/questions/{question_id}/versions`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明         |
| ------------- | ------ | ------------ |
| `question_id` | String | 题目谱系 ID  |

**请求体**：

```json
{
  "type": "single_choice",
  "title": "您对我们的服务满意吗？（修订版）",
  "required": true,
  "options": [
    { "option_id": "opt1", "text": "非常满意" },
    { "option_id": "opt2", "text": "满意" },
    { "option_id": "opt3", "text": "不满意" }
  ],
  "validation": {},
  "parent_version_number": 1
}
```

| 字段                    | 类型    | 必填 | 说明                           |
| ----------------------- | ------- | ---- | ------------------------------ |
| `type`                  | String  | 是   | 题目类型                       |
| `title`                 | String  | 是   | 题目文本（1-500 字符）         |
| `required`              | Boolean | 否   | 是否必答，默认 `true`          |
| `options`               | Array   | 否   | 选项列表                       |
| `validation`            | Object  | 否   | 校验规则                       |
| `parent_version_number` | Number  | 否   | 基于哪个版本创建（可选，用于记录版本树关系） |

说明：创建者和被共享者均可创建新版本。

**成功响应 data**：

```json
{
  "question_id": "664a1b2c3d4e5f6789012345",
  "version_number": 3,
  "created_at": "2026-04-03T00:00:00Z"
}
```

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 4001   | 题目不存在       |
| 4002   | 指定的父版本不存在 |
| 2002   | 无权限操作该题目 |

---

### 7.7 获取版本历史

- **方法**：`GET`
- **路径**：`/questions/{question_id}/versions`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明         |
| ------------- | ------ | ------------ |
| `question_id` | String | 题目谱系 ID  |

**请求体**：无

**成功响应 data**：

```json
[
  {
    "version_number": 1,
    "created_at": "2026-04-01T00:00:00Z",
    "updated_by": "507f1f77bcf86cd799439011",
    "parent_version_number": null,
    "title": "您对我们的服务满意吗？",
    "type": "single_choice"
  },
  {
    "version_number": 2,
    "created_at": "2026-04-02T00:00:00Z",
    "updated_by": "507f1f77bcf86cd799439011",
    "parent_version_number": 1,
    "title": "您对我们的服务满意吗？（修订版）",
    "type": "single_choice"
  }
]
```

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 4001   | 题目不存在       |
| 2002   | 无权限操作该题目 |

---

### 7.8 恢复历史版本

- **方法**：`POST`
- **路径**：`/questions/{question_id}/versions/{version_number}/restore`
- **鉴权**：需要 JWT

**路径参数**：

| 参数             | 类型   | 说明               |
| ---------------- | ------ | ------------------ |
| `question_id`    | String | 题目谱系 ID        |
| `version_number` | Number | 要恢复的版本号     |

**请求体**：无

说明：基于目标旧版本的内容创建一个新版本，`parent_version_number` 指向被恢复的版本号。不会删除任何已有版本。

**成功响应 data**：

```json
{
  "question_id": "664a1b2c3d4e5f6789012345",
  "version_number": 4,
  "created_at": "2026-04-04T00:00:00Z"
}
```

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 4001   | 题目不存在       |
| 4002   | 指定版本不存在   |
| 2002   | 无权限操作该题目 |

---

### 7.9 共享题目

- **方法**：`POST`
- **路径**：`/questions/{question_id}/share`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明         |
| ------------- | ------ | ------------ |
| `question_id` | String | 题目谱系 ID  |

**请求体**：

```json
{
  "username": "target_user"
}
```

| 字段       | 类型   | 必填 | 说明               |
| ---------- | ------ | ---- | ------------------ |
| `username` | String | 是   | 共享目标用户的用户名 |

说明：仅题目创建者可以共享，不能共享给自己。重复共享不报错（幂等操作）。

**成功响应 data**：

```json
{
  "message": "已共享给用户「target_user」"
}
```

**可能的错误码**：

| 错误码 | 说明               |
| ------ | ------------------ |
| 4001   | 题目不存在         |
| 4004   | 目标用户不存在     |
| 2002   | 无权限（非创建者） |
| 3001   | 不能共享给自己     |

---

### 7.10 取消共享

- **方法**：`POST`
- **路径**：`/questions/{question_id}/unshare`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明         |
| ------------- | ------ | ------------ |
| `question_id` | String | 题目谱系 ID  |

**请求体**：

```json
{
  "username": "target_user"
}
```

| 字段       | 类型   | 必填 | 说明                   |
| ---------- | ------ | ---- | ---------------------- |
| `username` | String | 是   | 取消共享的目标用户用户名 |

说明：仅题目创建者可以取消共享。

**成功响应 data**：

```json
{
  "message": "已取消共享给用户「target_user」"
}
```

**可能的错误码**：

| 错误码 | 说明               |
| ------ | ------------------ |
| 4001   | 题目不存在         |
| 4004   | 目标用户不存在     |
| 2002   | 无权限（非创建者） |

---

### 7.11 加入题库

- **方法**：`POST`
- **路径**：`/questions/{question_id}/bank`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明         |
| ------------- | ------ | ------------ |
| `question_id` | String | 题目谱系 ID  |

**请求体**：无

说明：创建者和被共享者均可将题目加入自己的题库。重复加入不报错（幂等操作）。

**成功响应 data**：

```json
{
  "message": "已加入题库"
}
```

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 4001   | 题目不存在       |
| 2002   | 无权限操作该题目 |

---

### 7.12 移出题库

- **方法**：`DELETE`
- **路径**：`/questions/{question_id}/bank`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明         |
| ------------- | ------ | ------------ |
| `question_id` | String | 题目谱系 ID  |

**请求体**：无

**成功响应 data**：

```json
{
  "message": "已移出题库"
}
```

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 4001   | 题目不存在       |
| 2002   | 无权限操作该题目 |

---

### 7.13 查看题目使用情况

- **方法**：`GET`
- **路径**：`/questions/{question_id}/usage`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明         |
| ------------- | ------ | ------------ |
| `question_id` | String | 题目谱系 ID  |

**请求体**：无

说明：查询该题目被哪些问卷引用，以及引用的版本号。

**成功响应 data**：

```json
[
  {
    "survey_id": "507f1f77bcf86cd799439012",
    "survey_title": "用户满意度调查 A",
    "survey_status": "published",
    "version_number": 1
  },
  {
    "survey_id": "507f1f77bcf86cd799439013",
    "survey_title": "用户满意度调查 B",
    "survey_status": "draft",
    "version_number": 2
  }
]
```

**可能的错误码**：

| 错误码 | 说明             |
| ------ | ---------------- |
| 4001   | 题目不存在       |
| 2002   | 无权限操作该题目 |

---

### 7.14 删除题目

- **方法**：`DELETE`
- **路径**：`/questions/{question_id}`
- **鉴权**：需要 JWT

**路径参数**：

| 参数          | 类型   | 说明         |
| ------------- | ------ | ------------ |
| `question_id` | String | 题目谱系 ID  |

**请求体**：无

说明：

- 仅题目创建者可以删除
- 如果该题目有已发布（`published`）的问卷正在使用，则不允许删除

**成功响应 data**：`null`

**可能的错误码**：

| 错误码 | 说明                               |
| ------ | ---------------------------------- |
| 4001   | 题目不存在                         |
| 4003   | 题目被已发布问卷使用中，无法删除   |
| 2002   | 无权限（非创建者）                 |

---

## 8. 题目类型与数据结构参考

### 8.1 各题型 validation 字段

**单选题 (single_choice)**：无特殊校验字段，`validation` 传 `{}` 或 `null`。

**多选题 (multiple_choice)**：

| 字段             | 类型   | 说明                                     |
| ---------------- | ------ | ---------------------------------------- |
| `min_selected`   | Number | 最少选择数量                             |
| `max_selected`   | Number | 最多选择数量                             |
| `exact_selected` | Number | 必须选择的精确数量（优先级高于 min/max） |

**文本填空 (text_input)**：

| 字段         | 类型   | 说明     |
| ------------ | ------ | -------- |
| `min_length` | Number | 最少字数 |
| `max_length` | Number | 最多字数 |

**数字填空 (number_input)**：

| 字段           | 类型    | 说明           |
| -------------- | ------- | -------------- |
| `min_value`    | Number  | 最小值         |
| `max_value`    | Number  | 最大值         |
| `integer_only` | Boolean | 是否必须为整数 |

### 8.2 跳转逻辑结构

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

**`select_option`** -- 单选匹配（适用于 single_choice）：

```json
{
  "type": "select_option",
  "option_id": "opt4"
}
```

**`contains_option`** -- 多选包含（适用于 multiple_choice）：

```json
{
  "type": "contains_option",
  "option_ids": ["opt1", "opt2"],
  "match_type": "any"
}
```

`match_type`：`"any"` 表示选中任一即触发（OR），`"all"` 表示全部选中才触发（AND）。

**`number_compare`** -- 数字比较（适用于 number_input）：

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
{ "type": "jump_to", "target_question_id": "q5" }

// 直接结束问卷
{ "type": "end_survey" }
```

---

## 9. 错误码说明

### 9.1 完整错误码表

| 错误码 | 说明                             | HTTP 状态码 |
| ------ | -------------------------------- | ----------- |
| 1001   | 用户名已存在                     | 400         |
| 1002   | 用户名或密码错误                 | 400         |
| 1003   | Token 无效或已过期               | 401         |
| 2001   | 问卷不存在                       | 404         |
| 2002   | 无权限操作该问卷/题目            | 403         |
| 2003   | 问卷已关闭                       | 400         |
| 2004   | 问卷已过期                       | 400         |
| 2005   | 访问码无效                       | 400         |
| 3001   | 答案校验失败                     | 400         |
| 3002   | 不允许重复提交                   | 400         |
| 3003   | 必填题未回答                     | 400         |
| 3004   | 需要登录                         | 401         |
| 4001   | 题目不存在                       | 404         |
| 4002   | 题目版本不存在                   | 404         |
| 4003   | 题目被已发布问卷使用中，无法删除 | 400         |
| 4004   | 共享目标用户不存在               | 404         |

### 9.2 错误码分组

| 范围      | 模块     |
| --------- | -------- |
| 1001-1003 | 认证模块 |
| 2001-2005 | 问卷模块 |
| 3001-3004 | 答卷模块 |
| 4001-4004 | 题目模块（第二阶段新增） |
