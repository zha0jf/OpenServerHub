from typing import List
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import httpx

from app.core.database import get_db
from app.schemas.monitoring import MonitoringRecordResponse
from app.services.monitoring import MonitoringService
from app.services.server import ServerService
from app.services.auth import AuthService
from app.core.config import settings

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

@router.get("/prometheus/query")
async def query_prometheus_metrics(
    query: str = Query(..., description="Prometheus查询表达式"),
    time: str = Query(None, description="查询时间点"),
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """查询Prometheus监控数据"""
    try:
        # 构建Prometheus API URL
        prometheus_url = f"{settings.PROMETHEUS_URL}/api/v1/query"
        
        # 构建查询参数
        params = {"query": query}
        if time:
            params["time"] = time
            
        # 发送查询请求
        async with httpx.AsyncClient() as client:
            response = await client.get(prometheus_url, params=params)
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/prometheus/query_range")
async def query_prometheus_metrics_range(
    query: str = Query(..., description="Prometheus查询表达式"),
    start: str = Query(..., description="开始时间"),
    end: str = Query(..., description="结束时间"),
    step: str = Query("60s", description="时间步长"),
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """查询Prometheus监控数据范围"""
    try:
        # 构建Prometheus API URL
        prometheus_url = f"{settings.PROMETHEUS_URL}/api/v1/query_range"
        
        # 构建查询参数
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step
        }
            
        # 发送查询请求
        async with httpx.AsyncClient() as client:
            response = await client.get(prometheus_url, params=params)
            return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/alerts/webhook")
async def handle_alert_webhook(
    alert_data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """处理AlertManager告警Webhook"""
    try:
        # 记录告警信息到数据库
        # 这里可以添加具体的告警处理逻辑
        
        # 如果需要异步处理，可以添加到后台任务
        # background_tasks.add_task(process_alert, alert_data)
        
        return {"status": "success", "message": "告警已接收"}
    except Exception as e:
        return {"status": "error", "message": str(e)}