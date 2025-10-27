from fastapi import FastAPI
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
from app.services import scheduler_service

logger = logging.getLogger(__name__)

# 设置日志
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 启动定时任务服务（如果启用）
    if settings.POWER_STATE_REFRESH_ENABLED:
        try:
            await scheduler_service.start()
            logger.info("电源状态定时刷新服务已启动")
        except Exception as e:
            logger.error(f"启动定时任务服务失败: {e}")
    
    yield
    
    # 关闭时停止定时任务服务
    try:
        await scheduler_service.stop()
        logger.info("电源状态定时刷新服务已停止")
    except Exception as e:
        logger.error(f"停止定时任务服务失败: {e}")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# 配置CORS - 统一处理开发和生产环境
# 从环境变量获取CORS配置，如果未设置则使用默认值
cors_origins = settings.BACKEND_CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
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

@app.get("/api/v1/scheduler/status")
async def get_scheduler_status():
    """获取定时任务状态"""
    try:
        status = scheduler_service.get_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"获取定时任务状态失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@app.post("/api/v1/scheduler/refresh-power-state")
async def manual_refresh_power_state():
    """手动刷新所有服务器电源状态"""
    try:
        await scheduler_service.refresh_all_servers_power_state()
        return {
            "success": True,
            "message": "电源状态刷新任务已提交"
        }
    except Exception as e:
        logger.error(f"手动刷新电源状态失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }