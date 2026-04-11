# 第二阶段 README

## 项目简介

在线问卷系统第二阶段，在第一阶段的基础上新增了题目独立管理、版本控制、团队共享、题库、跨问卷统计等功能。

## 技术栈

- **后端**：Python 3.12 + FastAPI + MongoDB (pymongo)
- **前端**：React 18 + TypeScript + Vite + Axios
- **测试**：Pytest（61 个自动化测试）

## 第二阶段新增功能

1. **题目独立保存与复用** - 题目从问卷中独立出来，可被多个问卷引用
2. **题目共享** - 按用户名定向共享题目给团队成员
3. **题目版本管理** - 每次修改创建新版本，历史版本不可变
4. **版本恢复** - 基于旧版本创建新版本
5. **不同版本并存** - 不同问卷可引用同一题目的不同版本
6. **使用关系查询** - 查看题目被哪些问卷使用
7. **题库管理** - 个人收藏夹功能
8. **跨问卷单题统计** - 按题目谱系聚合所有问卷的回答数据

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

### 后端
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

### 数据迁移（从第一阶段升级）
```bash
cd backend
python -m scripts.migrate_phase2
```

### 运行测试
```bash
cd 大作业一
.venv/Scripts/python -m pytest backend/tests/ -v
```

## 数据库设计

详见 `数据库设计2.md`

## API 文档

详见 `API说明2.md`
