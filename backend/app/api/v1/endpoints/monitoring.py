from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.schemas.monitoring import MonitoringRecordResponse
from app.services.monitoring import MonitoringService
from app.services.auth import AuthService

router = APIRouter()

@router.get("/servers/{server_id}/metrics", response_model=List[MonitoringRecordResponse])
async def get_server_metrics(
    server_id: int,
    metric_type: str = Query(None, description="指标类型：temperature, voltage, fan_speed"),
    hours: int = Query(24, description="获取最近N小时的数据"),
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取服务器监控指标"""
    monitoring_service = MonitoringService(db)
    since = datetime.now() - timedelta(hours=hours)
    return monitoring_service.get_server_metrics(
        server_id=server_id,
        metric_type=metric_type,
        since=since
    )

@router.post("/servers/{server_id}/collect")
async def collect_server_metrics(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """手动采集服务器指标"""
    monitoring_service = MonitoringService(db)
    result = await monitoring_service.collect_server_metrics(server_id)
    return result