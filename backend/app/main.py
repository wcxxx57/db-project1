from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.database import get_db, init_indexes, close_db
from app.routes import auth, surveys, responses, statistics
from app.utils.response import error_response, ErrorCodes


HTTP_STATUS_TO_BUSINESS_CODE = {
    400: ErrorCodes.ANSWER_VALIDATION_FAILED,
    401: ErrorCodes.INVALID_TOKEN,
    403: ErrorCodes.NO_PERMISSION,
    404: ErrorCodes.SURVEY_NOT_FOUND,
}

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
app.include_router(auth.router, prefix="/auth", tags=["用户认证"])
app.include_router(surveys.router, prefix="/surveys", tags=["问卷管理"])
app.include_router(responses.router, tags=["答卷提交"])
app.include_router(statistics.router, tags=["统计数据"])


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request, exc: RequestValidationError):
    """将 FastAPI 默认 422 统一转换为业务错误响应。"""
    message = "请求参数校验失败"
    details = exc.errors()

    for err in details:
        loc = err.get("loc", ())
        err_type = err.get("type", "")
        if isinstance(loc, tuple) and "username" in loc:
            if "too_short" in err_type:
                message = "用户名不足2位，请至少输入2位"
                break
            if "too_long" in err_type:
                message = "用户名超过50位，请输入不超过50位"
                break
        if isinstance(loc, tuple) and "password" in loc:
            if "too_short" in err_type:
                message = "密码不足8位，请至少输入8位"
                break
            if "too_long" in err_type:
                message = "密码超过128位，请输入不超过128位"
                break

    return JSONResponse(
        status_code=400,
        content=error_response(
            code=ErrorCodes.ANSWER_VALIDATION_FAILED,
            message=message,
            data={"details": details},
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """将 HTTPException 统一包装为业务响应结构。"""
    detail = exc.detail

    if isinstance(detail, dict):
        business_code = detail.get(
            "code",
            HTTP_STATUS_TO_BUSINESS_CODE.get(exc.status_code, exc.status_code),
        )
        message = detail.get("message", "请求失败")
        data = detail.get("data")
    else:
        business_code = HTTP_STATUS_TO_BUSINESS_CODE.get(exc.status_code, exc.status_code)
        message = detail if isinstance(detail, str) else "请求失败"
        data = None

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code=business_code, message=message, data=data),
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the Survey System API!"}
