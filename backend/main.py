from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os
import asyncio

from app.core.config import settings
from app.core.database import engine, periodic_health_check
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.models import Base

from app.services.monitoring_scheduler import MonitoringSchedulerService  # 导入类本身
# from app.services.ipmi import ipmi_pool  # 已移除，因切换到多进程实现

# Prometheus指标导出
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    import time
    
    # 创建指标
    REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
    REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
except ImportError:
    # 如果没有安装prometheus-client，则不启用指标功能
    Counter = Histogram = generate_latest = CONTENT_TYPE_LATEST = None
    time = None
    REQUEST_COUNT = REQUEST_DURATION = None

logger = logging.getLogger(__name__)

# 设置日志
setup_logging()

logger.debug(f"[应用启动] DEBUG环境变量值: '{os.getenv('DEBUG', '')}'")
logger.debug(f"[应用启动] 当前日志级别: {logging.getLogger().level}")


# 导入监控调度服务模块（注意：不是实例）
import app.services.monitoring_scheduler as monitoring_module

# 健康检查任务引用
health_check_task = None

# 电源状态定时刷新服务引用
power_state_scheduler_service = None

# 离线服务器检查服务引用
offline_server_checker_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global health_check_task
    
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 启动数据库健康检查任务
    try:
        health_check_task = asyncio.create_task(periodic_health_check())
        logger.info("数据库健康检查任务已启动")
    except Exception as e:
        logger.error(f"启动数据库健康检查任务失败: {e}")
    
    # 打印配置值用于调试
    logger.info(f"POWER_STATE_REFRESH_ENABLED 配置值: {settings.POWER_STATE_REFRESH_ENABLED}")
    logger.info(f"POWER_STATE_REFRESH_INTERVAL 配置值: {settings.POWER_STATE_REFRESH_INTERVAL}")
    
    # 初始化并启动电源状态定时刷新服务（如果启用）
    global power_state_scheduler_service
    if settings.POWER_STATE_REFRESH_ENABLED:
        try:
            from app.services.scheduler_service import PowerStateSchedulerService
            from app.services import scheduler_service as scheduler_service_global
            power_state_scheduler_service = PowerStateSchedulerService()
            # 同时初始化scheduler_service全局变量
            scheduler_service_global.scheduler_service = power_state_scheduler_service
            await power_state_scheduler_service.start()
            logger.info("电源状态定时刷新服务已启动")
        except Exception as e:
            logger.error(f"启动电源状态定时任务服务失败: {e}")
    
    # 在安全的环境里实例化并启动监控数据采集定时任务服务
    try:
        monitoring_module.monitoring_scheduler_service = MonitoringSchedulerService()
        await monitoring_module.monitoring_scheduler_service.start()
        logger.info("监控数据采集定时任务服务已启动")
    except Exception as e:
        logger.error(f"启动监控数据采集定时任务服务失败: {e}")
    
    # 初始化并启动离线服务器检查服务
    global offline_server_checker_service
    try:
        from app.services.offline_server_checker import OfflineServerCheckerService
        offline_server_checker_service = OfflineServerCheckerService()
        await offline_server_checker_service.start()
        logger.info("离线服务器检查服务已启动")
    except Exception as e:
        logger.error(f"启动离线服务器检查服务失败: {e}")
    
    yield
    
    # 关闭时停止电源状态定时刷新服务
    try:
        if power_state_scheduler_service:
            await power_state_scheduler_service.stop()
            logger.info("电源状态定时刷新服务已停止")
    except Exception as e:
        logger.error(f"停止电源状态定时任务服务失败: {e}")
    
    # 停止监控数据采集定时任务服务
    try:
        if monitoring_module.monitoring_scheduler_service:
            await monitoring_module.monitoring_scheduler_service.stop()
        logger.info("监控数据采集定时任务服务已停止")
    except Exception as e:
        logger.error(f"停止监控数据采集定时任务服务失败: {e}")
    
    # 关闭时停止离线服务器检查服务
    try:
        if offline_server_checker_service:
            await offline_server_checker_service.stop()
            logger.info("离线服务器检查服务已停止")
    except Exception as e:
        logger.error(f"停止离线服务器检查服务失败: {e}")
    
    # 停止数据库健康检查任务
    if health_check_task:
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass
        logger.info("数据库健康检查任务已停止")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

# 添加Prometheus指标中间件（如果可用）
if REQUEST_COUNT is not None and REQUEST_DURATION is not None and time is not None:
    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        """Prometheus指标收集中间件"""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 记录请求计数和持续时间
        endpoint = request.url.path
        method = request.method
        status_code = response.status_code
        
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(process_time)
        
        return response

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

# 添加Prometheus指标端点（如果可用）
if generate_latest is not None and CONTENT_TYPE_LATEST is not None:
    @app.get("/metrics")
    async def metrics():
        """Prometheus指标端点"""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

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

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/scheduler/status")
async def get_scheduler_status():
    """获取定时任务状态"""
    try:
        power_status = power_state_scheduler_service.get_status() if power_state_scheduler_service else {}
        # 使用模块中的实例
        monitoring_status = monitoring_module.monitoring_scheduler_service.get_status() if monitoring_module.monitoring_scheduler_service else {}
        # 离线服务器检查服务状态
        offline_checker_status = offline_server_checker_service.get_status() if offline_server_checker_service else {}
        return {
            "success": True,
            "data": {
                "power_state_scheduler": power_status,
                "monitoring_scheduler": monitoring_status,
                "offline_server_checker": offline_checker_status
            }
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
        if power_state_scheduler_service:
            await power_state_scheduler_service.refresh_all_servers_power_state()
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

# 在生产环境中提供前端静态文件
# 注意：必须在所有API路由和端点之后挂载静态文件服务，以避免路由冲突
if settings.ENVIRONMENT == "production":
    # 在生产环境中，前端静态文件位于后端static目录中
    frontend_static_path = os.path.join(os.path.dirname(__file__), "static")
    
    if os.path.isdir(frontend_static_path):
        # 使用自定义的StaticFiles类来处理SPA路由
        class SPAStaticFiles(StaticFiles):
            async def get_response(self, path: str, scope):
                try:
                    return await super().get_response(path, scope)
                except:
                    # 如果文件不存在，返回index.html让前端路由处理
                    return await super().get_response("index.html", scope)
        
        app.mount("/", SPAStaticFiles(directory=frontend_static_path, html=True), name="frontend")

# 根路径端点 - 在生产环境中会被静态文件服务覆盖，在开发环境中提供API响应
@app.get("/")
async def root():
    return {"message": "OpenServerHub API Server"}