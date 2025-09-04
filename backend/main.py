from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import engine
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.models import Base

logger = logging.getLogger(__name__)

# 设置日志
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)
    yield
    # 关闭时的清理工作（如果需要）

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="OpenServerHub - 服务器管理平台",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

# 全局422错误处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    logger.warning(f"请求验证失败 {request.url}: {exc.errors()}")
    
    # 格式化错误信息
    errors = []
    for error in exc.errors():
        field = ' -> '.join(str(loc) for loc in error['loc'][1:])  # 跳过'body'
        message = error['msg']
        errors.append(f"{field}: {message}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "请求参数验证失败",
            "errors": errors,
            "message": "; ".join(errors)
        },
    )

@app.get("/")
async def root():
    return {"message": "OpenServerHub API Server"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}