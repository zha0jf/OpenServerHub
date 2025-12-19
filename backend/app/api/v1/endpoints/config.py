from fastapi import APIRouter, Depends
from app.core.config import settings
from app.services.auth import get_current_user

router = APIRouter()

@router.get("/")
async def get_frontend_config(current_user = Depends(get_current_user)):
    """获取前端配置信息"""
    return {
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