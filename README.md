# 在线问卷系统项目说明

本项目是一个基于 **MongoDB + FastAPI + React** 的在线问卷系统（第一阶段）

核心能力包括：
- 用户注册、登录、JWT 鉴权
- 问卷创建、编辑、发布、关闭、删除
- 四类题型（单选、多选、文本、数字）
- 数据驱动跳转逻辑
- 答卷提交与统计分析
- 自动化测试

---

## 1. 项目文档说明

仓库根目录下的文档作用如下：

- [系统说明.md](系统说明.md)：系统功能、业务流程、模块设计的总体说明
- [数据库设计.md](数据库设计.md)：MongoDB 集合设计、字段说明、索引策略、建模理由，包含 `users / surveys / responses` 三集合关系。
- [API说明.md](API说明.md)：后端接口协议定义（请求、响应、错误码、鉴权规则），前后端联调参考
- [关键逻辑说明.md](关键逻辑说明.md)：跳转逻辑、校验策略、提交流程等核心业务逻辑说明
- [测试用例.md](测试用例.md)：自动化测试用例输入输出与验证结果，相应测试代码在 `backend/tests/` 
- [配置说明.md](配置说明.md)：环境配置、运行参数、依赖安装等说明
- [AI使用过程.md](AI使用过程.md)：记录 AI 辅助开发的 prompt、产出、人工修正，包含：AI 帮了什么、做错了什么、如何修正”。
- [项目完成报告.md](项目完成报告.md)：**最终文档**，pdf版本已提交水杉在线

## 2. 项目大致目录

```text
大作业一/
├─ backend/                    # FastAPI 后端
│  ├─ app/
│  │  ├─ main.py               # 应用入口
│  │  ├─ config.py             # 配置读取
│  │  ├─ database.py           # MongoDB 连接与索引初始化
│  │  ├─ models/               # Pydantic 模型
│  │  ├─ routes/               # 路由层（auth/surveys/responses/statistics）
│  │  ├─ services/             # 业务逻辑层
│  │  └─ middlewares/          # JWT 鉴权中间件
│  ├─ tests/                   # pytest 测试
│  └─ requirements.txt         # Python 依赖
│
├─ frontend/                   # React + Vite 前端
│  ├─ src/
│  │  ├─ components/           # 页面核心组件（Dashboard/Editor/Fill/Statistics）
│  │  ├─ pages/                # 页面入口
│  │  ├─ services/             # API 调用层
│  │  ├─ types/                # TypeScript 类型定义
│  │  ├─ App.tsx               # 前端应用入口
│  │  └─ App.css               # 样式
│  └─ package.json             # Node 依赖与脚本
│
├─ doc_pic/                    # 文档截图与示意图
├─ *.md                        # 设计、接口、测试、报告等文档
└─ README.md                   # 当前说明文件
```

---

## 3. 项目内容总览

### 后端（`backend/`）
- 框架：FastAPI
- 数据库：MongoDB（PyMongo）
- 能力：鉴权、问卷管理、答卷提交、统计分析、规则校验
- 特点：
  - 统一响应格式 `{code, message, data}`
  - 业务层与路由层解耦
  - 跳转逻辑与校验逻辑可配置（数据驱动）

### 前端（`frontend/`）
- 框架：React + Vite + TypeScript
- 核心页面：
  - Dashboard（问卷列表与操作）
  - SurveyEditor（问卷编辑与逻辑配置）
  - SurveyFill（填写问卷）
  - StatisticsView（统计展示）
- 特点：
  - 与后端 API 对齐的类型定义
  - 与后端一致的部分业务规则校验

### 测试（`backend/tests/`）
- 使用 `pytest`
- 覆盖认证、问卷管理、答卷提交、统计、跳转校验等核心流程

---

## 4. 快速开始

### 4.1 启动后端

```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### 4.2 启动前端

```powershell
cd frontend
npm install
npm run dev
```

### 4.3 运行测试

```powershell
cd backend
python -m pytest tests -q
```

---

## 5.贡献者

