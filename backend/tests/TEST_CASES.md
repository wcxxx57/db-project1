# 第一阶段测试用例（自动化 + API）

说明：以下测试用例均已在 `pytest` 中实现，对应文件为 `test_surveys.py`、`test_responses.py`、`test_statistics.py`。

## 1. 创建问卷测试

### 用例 1.1 创建问卷成功并校验数据结构
- 测试步骤
1. 调用 `POST /surveys` 提交标题、描述、settings。
2. 检查返回体 `code/message/data` 结构。
3. 检查数据库 `surveys` 文档字段完整性。
- 输入
1. `title=课程反馈`
2. `settings.allow_anonymous=true`
3. `settings.allow_multiple=false`
- 输出
1. HTTP 200
2. `code=0`
3. 返回 `survey_id/access_code/status/created_at`
- 结果
1. 新问卷状态为 `draft`
2. `questions=[]`
3. `response_count=0`

## 2. 添加题目测试

### 用例 2.1 编辑问卷并添加多题型题目
- 测试步骤
1. 先创建问卷。
2. 调用 `PUT /surveys/{survey_id}` 写入题目数组。
3. 校验题目顺序、题型、校验字段和逻辑字段持久化。
- 输入
1. 单选题 `q1`
2. 文本题 `q2`
3. 数字题 `q3`
- 输出
1. HTTP 200
2. 返回问卷包含 3 道题
- 结果
1. `question_id/type/order` 保持一致
2. `logic.rules` 和 `validation` 正确保存

## 3. 跳转逻辑测试

### 用例 3.1 跳转后跳过非路径必填题
- 测试步骤
1. 创建并发布含跳转规则问卷（`q1(opt_yes)->q3`）。
2. 提交答案仅包含 `q1=opt_yes` 与 `q3`。
3. 检查提交是否成功。
- 输入
1. `q1=opt_yes`
2. `q3=5`
- 输出
1. HTTP 200
2. `code=0`
- 结果
1. 服务端按路径动态计算必答题
2. `q2` 不在路径中时不会误判必填缺失

### 用例 3.2 实际路径缺少必填题应失败
- 测试步骤
1. 使用同一问卷提交 `q1=opt_no`（顺序进入 `q2`）。
2. 故意不提交 `q2`。
3. 检查错误码。
- 输入
1. `q1=opt_no`
2. 缺失 `q2`
- 输出
1. HTTP 400
2. `code=3003`
- 结果
1. 返回“必填题未回答”错误

## 4. 校验测试

### 用例 4.1 数字题整数约束校验
- 测试步骤
1. 创建并发布包含 `integer_only=true` 的数字题。
2. 提交小数答案。
3. 检查错误码与错误文案。
- 输入
1. `q3=3.5`
- 输出
1. HTTP 400
2. `code=3001`
- 结果
1. 返回“必须为整数”

### 用例 4.2 匿名策略校验
- 测试步骤
1. 创建 `allow_anonymous=false` 问卷并发布。
2. 提交时设置 `is_anonymous=true`。
3. 检查业务错误。
- 输入
1. `is_anonymous=true`
- 输出
1. HTTP 400
2. `code=3001`
- 结果
1. 返回“该问卷不允许匿名填写”

## 5. 提交问卷测试

### 用例 5.1 重复提交限制
- 测试步骤
1. 创建 `allow_multiple=false` 问卷并发布。
2. 同一用户提交两次。
3. 校验第二次返回。
- 输入
1. 第一次合法答案
2. 第二次合法答案
- 输出
1. 第一次 HTTP 200
2. 第二次 HTTP 400 + `code=3002`
- 结果
1. 正确拦截重复提交

## 6. 统计测试

### 用例 6.1 问卷整体统计（单选/多选/文本/数字）
- 测试步骤
1. 创建多题型问卷并发布。
2. 两个不同用户分别提交实名与匿名答卷。
3. 调用 `GET /surveys/{survey_id}/statistics`。
4. 校验各题聚合结果。
- 输入
1. 单选：`opt_py`/`opt_js`
2. 多选：`[opt_git,opt_ci]`、`[opt_git]`
3. 文本：两条字符串
4. 数字：3 与 5
- 输出
1. HTTP 200
2. `total_responses=2`
3. 返回每题统计对象
- 结果
1. 计数正确：`opt_git=2`
2. 文本列表包含两条输入
3. 数字统计 `average=4.0, min=3, max=5`

### 用例 6.2 单题统计中的实名/匿名显示规则
- 测试步骤
1. 创建问卷并提交一条实名、一条匿名答卷。
2. 调用 `GET /surveys/{survey_id}/questions/{question_id}/statistics`。
3. 检查 respondents 列表。
- 输入
1. `q_single=opt_py`
- 输出
1. HTTP 200
2. `option_statistics[].respondents` 含 2 条记录
- 结果
1. 实名用户显示用户名
2. 匿名用户显示 `匿名用户`，且不暴露 `respondent_id`
