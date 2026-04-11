# 第二阶段实现计划（给ai的）

## 1. 目标

在第一阶段现有工程基础上完成第二阶段需求，不推倒重做，保留原有登录鉴权、问卷管理、填写、统计、跳转逻辑与统一 JSON 返回结构。

本阶段新增能力：
- 题目独立保存、复用、共享
- 题目版本管理、历史追踪、恢复旧版本
- 同一题目不同版本并存，问卷可绑定指定版本
- 查看题目被哪些问卷使用
- 个人题库管理
- 跨问卷单题统计

## 2. 第一阶段现状与改造方向

现状：
- `surveys.questions` 直接内嵌完整题目，题目只属于单个问卷
- `responses.answers` 只记录 `question_id + answer`，无法做跨问卷单题统计
- 题目没有独立实体、没有版本链、没有共享入口
- 前端编辑器直接编辑问卷内嵌题目

改造方向：
- 引入独立 `questions` 集合管理题目谱系与版本
- `surveys.questions` 改为“问卷局部上下文 + 题目版本引用”
- `responses.answers` 增加 `question_ref_id`、`version_number`
- 保留现有问卷主流程，但问卷编辑、填写、统计全部改为围绕“题目引用版本”执行

## 3. 数据模型落地范围

严格按 数据库设计2.md 落地：

### 3.1 questions 集合
- 新增独立题目集合
- 每个文档表示一个题目谱系
- 文档内使用 `versions` 数组保存全部历史版本
- 顶层维护 `latest_version_number`
- 顶层 `access_control` 管理：
  - `creator`
  - `shared_with`
  - `banked_by`

### 3.2 surveys 集合
- `questions` 不再内嵌完整题目内容
- 每个问卷题目项仅保存：
  - `question_id`
  - `order`
  - `logic`
  - `question_ref_id`
  - `version_number`

### 3.3 responses 集合
- `answers` 每项增加：
  - `question_ref_id`
  - `version_number`
- 保留原有 `question_id` 与 `answer`

### 3.4 题库实现方式
- 不新增独立 `question_banks` collection
- 题库即 `questions.access_control.banked_by`
- 本阶段只做“个人题库/收藏夹”，不做命名分类题库

## 4. 核心业务规则

### 4.1 题目版本规则
- 创建题目时自动生成 v1
- 修改题目一律创建新版本，不原地覆盖旧版本
- 恢复旧版本时，基于目标旧版本内容创建一个新版本
- 已写入的历史版本不可修改、不可删除

### 4.2 共享规则
- 仅题目创建者可彻底删除题目（删除后所有贡献者都将看不见这个题目），不过也是在没有‘已发布’的问卷中没有使用该题目的任何版本才可以删除；可删除参与共享的用户
- 共享对象可查看、引用到自己的问卷、加入自己的题库、创建该题目的新版本等；基本和创建者权限差不多，方便团队协作
- 本阶段只做“按用户名定向共享”，不做公开共享

### 4.3 问卷编辑规则
- 草稿问卷允许增删题、排序、替换引用版本、创建新的问题版本（版本改变都是仅改变当前问卷的引用版本，不改变其他无论什么状态的也用到这个问题的问卷）、调整逻辑
- 发布后问卷题目结构冻结
- 关闭后仍按当前第一阶段规则允许编辑问卷元信息，不过如果题目版本改变，改变前后收集的问卷的结果会分开显示，不能和之前版本收集到的结果混在一起
- 问卷中的局部逻辑始终使用 `question_id`，不使用 `question_ref_id`

### 4.4 统计规则
- 保留原有按问卷统计
- 新增按 `question_ref_id` 聚合的跨问卷单题统计
- 统计结果需能区分不同 `version_number`
- 返回命中的问卷列表，便于追踪使用来源

### 4.5 使用关系规则
- 可按题目谱系查看所有使用中的问卷
- 可按题目版本查看具体被哪些问卷引用

## 5. 后端实施计划

### 阶段 A：模型与索引调整
- 新增 `backend/app/models/question.py`
- 修改 `backend/app/models/survey.py`
- 修改 `backend/app/models/response.py`
- 修改 `backend/app/database.py`

具体内容：
- 定义题目版本、访问控制、题目列表/详情、共享、恢复等 Pydantic 模型
- 将问卷题目模型改为“引用模型”，保留 `logic`
- 为答卷答案模型补充 `question_ref_id`、`version_number`
- 初始化以下索引：
  - `questions.access_control.creator`
  - `questions.access_control.shared_with`
  - `questions.access_control.banked_by`
  - `surveys.questions.question_ref_id`
  - `responses.answers.question_ref_id`

### 阶段 B：题目域服务与接口
- 新增 `backend/app/services/question_service.py`
- 新增 `backend/app/routes/questions.py`

接口范围：
- 创建题目
- 查询我的题目
- 查询共享给我的题目
- 查询我的题库题目
- 查询题目详情
- 创建新版本
- 查询版本历史
- 恢复某历史版本
- 共享/取消共享题目
- 加入题库/移出题库
- 查询题目使用情况

### 阶段 C：问卷服务改造
- 重构 `backend/app/services/survey_service.py`
- 修改 `backend/app/routes/surveys.py`

改造重点：
- 问卷更新接口接收“题目引用列表”而不是完整题目定义
- 保存问卷时校验 `question_ref_id + version_number` 是否存在且当前用户有使用权限
- 编辑问卷时批量补全被引用题目的版本内容，返回前端展示所需完整题面
- 发布前校验逻辑改为基于“已解析出的题目版本内容 + 问卷局部 logic”执行
- 问卷公开填写接口返回已解析完成的题目内容，前端填写端不感知引用细节

### 阶段 D：答卷服务改造
- 重构 `backend/app/services/response_service.py`
- 修改 `backend/app/routes/responses.py`

改造重点：
- 提交答卷前先解析问卷引用的题目版本
- 校验、跳转、必填判断全部基于解析后的题目版本内容
- 写入答卷时补齐 `question_ref_id`、`version_number`

### 阶段 E：统计服务改造
- 重构 `backend/app/services/statistics_service.py`
- 修改 `backend/app/routes/statistics.py`

新增/调整能力：
- 按问卷统计时，统计对象改为解析后的题目版本
- 新增跨问卷单题统计接口
- 新增题目使用关系统计接口或并入题目详情接口

### 阶段 F：应用接入
- 修改 `backend/app/main.py`
- 注册 `questions` 路由
- 更新错误码映射与 `API说明.md`

### 阶段 G：一次性数据迁移
- 新增迁移脚本，处理第一阶段已有数据

迁移范围：
- 从现有 `surveys.questions` 抽取题目，写入 `questions` 集合并建立版本 v1
- 回填 `surveys.questions[*].question_ref_id`、`version_number`
- 对已有 `responses.answers` 回填 `question_ref_id`、`version_number`

说明：
- 采用一次性迁移，不写长期兼容双结构代码

## 6. 前端实施计划

### 阶段 A：类型与 API 改造
- 修改 `frontend/src/types/index.ts`
- 修改 `frontend/src/services/api.ts`

新增类型：
- 题目谱系
- 题目版本
- 问卷题目引用项
- 题目使用关系
- 跨问卷单题统计结果

### 阶段 B：题目管理界面
- 在现有 `Dashboard` 中增加题目管理入口，优先复用现有页面组织方式
- 新增“我的题库/共享给我的题目”三类列表
- 支持新建题目、查看详情、创建新版本、恢复版本、共享、加入题库、查看使用情况

### 阶段 C：问卷编辑器改造
- 重构 `frontend/src/components/SurveyEditor.tsx`

改造重点：
- 编辑器题目列表改为维护“问卷局部字段 + 引用题目版本”
- 支持从我的题目、共享题目、题库中选题加入问卷
- 支持在编辑器中直接新建题目后加入当前问卷
- 支持查看每道题当前引用的版本号
- 支持替换为同谱系其他版本
- 跳转逻辑仍绑定问卷内 `question_id`

### 阶段 D：填写页改造
- 修改 `frontend/src/components/SurveyFill.tsx`

改造重点：
- 保持现有填写体验
- 仅消费后端已解析的完整题目内容，不在前端处理题目版本解析

### 阶段 E：统计页改造
- 修改 `frontend/src/components/StatisticsView.tsx`
- 增加跨问卷单题统计视图
- 增加“被哪些问卷使用”展示

## 7. 测试计划

后端新增/修改测试：
- `backend/tests/test_surveys.py`
- `backend/tests/test_responses.py`
- `backend/tests/test_statistics.py`
- `backend/tests/test_jump_validation.py`
- 新增 `backend/tests/test_questions.py`

覆盖点：
- 创建题目与查询列表
- 创建新版本与版本链查询
- 恢复旧版本生成新版本
- 定向共享与权限校验
- 加入题库/移出题库
- 问卷保存题目引用成功
- 问卷发布后旧版本不受后续新版本影响
- 不同问卷可引用同谱系不同版本
- 题目使用情况查询正确
- 跨问卷单题统计正确
- 第一阶段已有数据迁移后可继续查询、填写、统计

## 8. 文档更新计划

需要同步新建以下文档（注意是新建）：
- `关键逻辑说明2.md`
- `API说明2.md`
- `测试用例2.md`
- `README2.md`
- `项目完成报告2.md`

补充重点：
- 第一阶段的设计是什么 
- 新需求带来了哪些问题 
- 为什么需要修改原设计 
- 修改了哪些部分 
- 数据结构如何变化 
- 程序如何调整 
- 是否遇到兼容性问题 
- 如何保证旧功能仍然可用 

即需要清楚记录整个修改过程。

## 9. 实施顺序

1. 完成题目域模型、问卷引用模型、答卷答案模型与索引改造
2. 完成题目域服务与接口
3. 完成问卷服务改造
4. 完成答卷与统计服务改造
5. 完成一次性数据迁移脚本
6. 完成前端类型、API、题目管理、编辑器、统计页改造
7. 完成自动化测试
8. 完成文档更新

## 10. 开发前确认的问题

### A. 关闭后的问卷允许继续改题
### B. 跨问卷单题统计默认口径
按照默认按题目谱系聚合，并在结果中按 `version_number` 分组展示

### C. 共享目标输入形式
前端按用户名输入，后端转用户 ID 校验
