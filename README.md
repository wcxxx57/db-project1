# 在线问卷系统项目说明

## 项目简介

在线问卷系统第二阶段，在第一阶段的基础上新增了题目独立管理、版本控制、团队共享、题库、跨问卷统计等功能。

## 技术栈

- **后端**：Python 3.12 + FastAPI + MongoDB (pymongo)
- **前端**：React 18 + TypeScript + Vite + Axios
- **测试**：Pytest（66 个自动化测试）

## 第二阶段新增功能

1. **题目独立保存与复用** - 题目从问卷中独立出来，可被多个问卷引用
2. **题目共享** - 按用户名定向共享题目给团队成员
3. **题目版本管理** - 每次修改创建新版本，历史版本不可变
4. **版本恢复** - 基于旧版本创建新版本
5. **不同版本并存** - 不同问卷可引用同一题目的不同版本
6. **使用关系查询** - 查看题目被哪些问卷使用
7. **题库管理** - 个人收藏夹功能，可区分“我的题目”“共享给我”“我的题库”三类来源
8. **跨问卷单题统计** - 按题目谱系聚合所有问卷的回答数据

## 项目文档说明
仓库根目录下的文档作用如下：

- [项目完成报告2.md](项目完成报告2.md)：**第二阶段最终文档**，pdf版本已提交水杉在线
- [数据库设计.md](数据库设计.md)：第二阶段的MongoDB 集合设计与变更说明，主要变化是新增了独立的 `questions` 集合，并将问卷与答卷中的题目从"直接嵌入内容"改为"存引用 id + 版本号"
- [系统说明.md](系统说明.md)：系统功能、业务流程、模块设计的总体说明
- [API说明.md](API说明.md)：后端接口协议定义（请求、响应、错误码、鉴权规则），前后端联调参考
- [关键逻辑说明.md](关键逻辑说明.md)：第二阶段新增题目管理相关业务的逻辑说明
- [测试用例.md](测试用例.md)：第二阶段自动化测试用例输入输出与验证结果，相应测试代码在 `backend/tests/` 
- [配置说明.md](配置说明.md)：环境配置、运行参数、依赖安装等说明
- [AI使用过程.md](AI使用过程.md)：记录第二阶段 AI 辅助开发的 prompt、产出、人工修正，包含：AI 帮了什么、做错了什么、如何修正”。

## 项目结构

```
backend/
├── app/
│   ├── main.py                     # FastAPI 入口
│   ├── config.py                   # 配置
│   ├── database.py                 # MongoDB 连接与索引
│   ├── models/
│   │   ├── user.py                 # 用户模型
│   │   ├── survey.py               # 问卷模型（含 SurveyQuestionRef）
│   │   ├── response.py             # 答卷模型
│   │   └── question.py             # 题目模型（第二阶段新增）
│   ├── services/
│   │   ├── auth_service.py         # 认证服务
│   │   ├── survey_service.py       # 问卷服务（已改造）
│   │   ├── response_service.py     # 答卷服务（已改造）
│   │   ├── statistics_service.py   # 统计服务（已改造+新增跨问卷）
│   │   └── question_service.py     # 题目服务（第二阶段新增）
│   ├── routes/
│   │   ├── auth.py
│   │   ├── surveys.py
│   │   ├── responses.py
│   │   ├── statistics.py           # 新增跨问卷统计接口
│   │   └── questions.py            # 题目路由（第二阶段新增）
│   ├── middlewares/
│   │   └── auth.py                 # JWT 认证中间件
│   └── utils/
│       └── response.py             # 统一响应格式
├── tests/
│   ├── conftest.py                 # 测试基础设施（已扩展）
│   ├── test_auth.py                # 14 个认证测试
│   ├── test_surveys.py             # 6 个问卷测试
│   ├── test_responses.py           # 13 个答卷测试
│   ├── test_statistics.py          # 2 个统计测试
│   ├── test_jump_validation.py     # 10 个跳转测试
│   └── test_questions.py           # 16 个题目测试（第二阶段新增）
└── scripts/
    └── migrate_phase2.py           # 数据迁移脚本

frontend/
├── src/
│   ├── App.tsx                     # 路由（新增 /questions）
│   ├── types/index.ts              # 类型定义（已扩展）
│   ├── services/api.ts             # API 客户端（已扩展）
│   ├── pages/
│   │   └── Dashboard.tsx           # 仪表盘（新增题目管理入口）
│   └── components/
│       ├── AuthModal.tsx           # 登录/注册
│       ├── SurveyEditor.tsx        # 问卷编辑器（已改造）
│       ├── SurveyFill.tsx          # 问卷填写
│       ├── StatisticsView.tsx      # 统计查看
│       └── QuestionManager.tsx     # 题目管理（第二阶段新增）
```

## 启动方式

### 安装依赖
```bash
cd backend
pip install -r requirements.txt  
```

### 数据迁移（从第一阶段升级）
```bash
cd backend
python -m scripts.migrate_phase2
```

### 启动后端
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### 启动前端
```bash
cd frontend
npm install
npm run dev
```

### 运行测试
```bash
cd db-project1
.venv/Scripts/python -m pytest backend/tests/ -v
```
