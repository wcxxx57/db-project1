from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import get_db, init_indexes, close_db
from app.routes import auth, surveys, responses, statistics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行：初始化数据库连接和索引
    get_db()
    init_indexes()
    yield
    # 关闭时执行
    close_db()

app = FastAPI(
    title="在线问卷系统 API",
    description="基于 MongoDB 和 FastAPI 的在线问卷系统后端",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 线上环境请按需修改
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由模块
# app.include_router(auth.router, prefix="/api/auth", tags=["用户认证"])
# app.include_router(surveys.router, prefix="/api/surveys", tags=["问卷管理"])
# app.include_router(responses.router, prefix="/api/responses", tags=["答卷提交"])
# app.include_router(statistics.router, prefix="/api/statistics", tags=["统计数据"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Survey System API!"}
