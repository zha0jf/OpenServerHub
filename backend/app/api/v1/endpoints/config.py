from fastapi import APIRouter, Depends
from app.core.config import settings
from app.services.auth import get_current_user
import logging

# 导入时间装饰器
from app.core.timing_decorator import timing_debug

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/public")
@timing_debug
async def get_public_frontend_config():
    """获取公开的前端配置信息（无需认证）"""
    logger.debug("[公共配置API] 收到获取公开配置信息请求")
    config_data = {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "vendor_name": settings.VENDOR_NAME,
        "vendor_url": settings.VENDOR_URL,
    }
    logger.debug(f"[公共配置API] 返回配置信息: {config_data}")
    return config_data

@router.get("/")
@timing_debug
async def get_frontend_config(current_user = Depends(get_current_user)):
    """获取前端配置信息（需要认证）"""
    logger.debug(f"[配置API] 用户 {current_user.username if current_user else 'unknown'} 请求配置信息")
    config_data = {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "grafana_url": settings.REACT_APP_GRAFANA_URL,
        "api_base_url": settings.API_V1_STR,
        "monitoring_enabled": settings.MONITORING_ENABLED,
        "monitoring_interval": settings.MONITORING_INTERVAL,
        "vendor_name": settings.VENDOR_NAME,
        "vendor_url": settings.VENDOR_URL,
    }
    logger.debug(f"[配置API] 返回配置信息: {config_data}")
    return config_data