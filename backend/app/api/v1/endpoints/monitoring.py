from typing import List
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import httpx
import logging

from app.core.database import get_db
from app.schemas.monitoring import MonitoringRecordResponse
from app.services.monitoring import MonitoringService
from app.services.server import ServerService
from app.services.auth import AuthService
from app.services.server_monitoring import GrafanaService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/servers/{server_id}/dashboard")
async def get_server_dashboard(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取服务器Grafana仪表板信息"""
    try:
        logger.info(f"获取服务器 {server_id} 的Grafana仪表板信息")
        
        # 检查服务器是否存在
        server_service = ServerService(db)
        server = server_service.get_server(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="服务器不存在")
        
        # 获取Grafana服务
        grafana_service = GrafanaService()
        
        # 当前使用固定UID的完整IPMI仪表板，通过var-instance参数区分服务器
        # 保留此API以备将来可能切换回基于服务器的专用仪表板
        dashboard_uid = "UKjaSZf7z"  # 固定使用完整IPMI仪表板
        dashboard_url = f"{grafana_service.grafana_url}/d/{dashboard_uid}"
        
        return {
            "dashboard_uid": dashboard_uid,
            "dashboard_url": dashboard_url,
            "server_id": server_id,
            "server_name": server.name,
            "server_status": server.status,  # 添加服务器状态信息
            "server_power_state": server.power_state  # 添加服务器电源状态信息
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取服务器 {server_id} Grafana仪表板信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取仪表板信息失败")

@router.get("/servers/{server_id}/metrics", response_model=List[MonitoringRecordResponse])
async def get_server_metrics(
    server_id: int,
    metric_type: str = Query(None, description="指标类型：temperature, voltage, fan_speed"),
    hours: int = Query(24, description="获取最近N小时的数据"),
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取服务器监控指标"""
    try:
        logger.info(f"获取服务器 {server_id} 监控指标，类型: {metric_type}, 时间范围: {hours}小时")
        
        # 验证参数
        if hours <= 0 or hours > 8760:  # 最多一年
            raise HTTPException(status_code=400, detail="时间范围必须在1小时到1年之间")
        
        monitoring_service = MonitoringService(db)
        since = datetime.now() - timedelta(hours=hours)
        
        metrics = monitoring_service.get_server_metrics(
            server_id=server_id,
            metric_type=metric_type,
            since=since
        )
        
        logger.info(f"成功获取服务器 {server_id} 的 {len(metrics)} 条监控记录")
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取服务器 {server_id} 监控指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取监控指标失败")

@router.post("/servers/{server_id}/collect")
async def collect_server_metrics(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """手动采集服务器指标"""
    try:
        logger.info(f"开始手动采集服务器 {server_id} 的监控指标")
        
        # 检查服务器是否存在
        server_service = ServerService(db)
        server = server_service.get_server(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="服务器不存在")
        
        monitoring_service = MonitoringService(db)
        result = await monitoring_service.collect_server_metrics(server_id)
        
        # 记录结果
        if result.get("status") == "success":
            logger.info(f"成功采集服务器 {server_id} 的监控指标: {len(result.get('collected_metrics', []))} 个指标")
        elif result.get("status") == "partial_success":
            logger.warning(f"部分成功采集服务器 {server_id} 的监控指标，存在错误: {result.get('errors', [])}")
        else:
            logger.error(f"采集服务器 {server_id} 监控指标失败: {result.get('message', 'Unknown error')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动采集服务器 {server_id} 监控指标时发生异常: {e}")
        raise HTTPException(status_code=500, detail="采集监控指标失败")

@router.get("/prometheus/query")
async def query_prometheus_metrics(
    query: str = Query(..., description="Prometheus查询表达式"),
    time: str = Query(None, description="查询时间点"),
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """查询Prometheus监控数据"""
    try:
        logger.info(f"查询Prometheus数据: {query}")
        
        # 验证查询参数
        if not query.strip():
            raise HTTPException(status_code=400, detail="查询表达式不能为空")
        
        # 构建Prometheus API URL
        prometheus_url = f"{settings.PROMETHEUS_URL}/api/v1/query"
        
        # 构建查询参数
        params = {"query": query}
        if time:
            params["time"] = time
            
        # 发送查询请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(prometheus_url, params=params)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Prometheus查询成功，返回 {len(result.get('data', {}).get('result', []))} 条结果")
            return result
            
    except httpx.TimeoutException:
        logger.error(f"Prometheus查询超时: {query}")
        raise HTTPException(status_code=504, detail="Prometheus查询超时")
    except httpx.HTTPStatusError as e:
        logger.error(f"Prometheus API错误: {e.response.status_code}")
        raise HTTPException(status_code=502, detail="Prometheus服务不可用")
    except Exception as e:
        logger.error(f"查询Prometheus数据失败: {e}")
        raise HTTPException(status_code=500, detail="查询监控数据失败")

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
        logger.info(f"查询Prometheus范围数据: {query}, 时间范围: {start} - {end}")
        
        # 验证查询参数
        if not query.strip():
            raise HTTPException(status_code=400, detail="查询表达式不能为空")
        if not start or not end:
            raise HTTPException(status_code=400, detail="开始时间和结束时间不能为空")
        
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
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(prometheus_url, params=params)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Prometheus范围查询成功，返回 {len(result.get('data', {}).get('result', []))} 个时间序列")
            return result
            
    except httpx.TimeoutException:
        logger.error(f"Prometheus范围查询超时: {query}")
        raise HTTPException(status_code=504, detail="Prometheus查询超时")
    except httpx.HTTPStatusError as e:
        logger.error(f"Prometheus API错误: {e.response.status_code}")
        raise HTTPException(status_code=502, detail="Prometheus服务不可用")
    except Exception as e:
        logger.error(f"查询Prometheus范围数据失败: {e}")
        raise HTTPException(status_code=500, detail="查询监控数据失败")

@router.post("/alerts/webhook")
async def handle_alert_webhook(
    alert_data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """处理AlertManager告警Webhook"""
    try:
        logger.info(f"收到告警Webhook: {alert_data.get('groupKey', 'unknown')}")
        
        # 验证告警数据
        if not alert_data.get('alerts'):
            logger.warning("收到空的告警数据")
            return {"status": "success", "message": "告警数据为空"}
        
        # 处理每个告警
        for alert in alert_data.get('alerts', []):
            alert_name = alert.get('labels', {}).get('alertname', 'Unknown')
            server_name = alert.get('labels', {}).get('server_name', 'Unknown')
            status = alert.get('status', 'unknown')
            
            logger.info(f"处理告警: {alert_name}, 服务器: {server_name}, 状态: {status}")
            
            # 这里可以添加具体的告警处理逻辑
            # 例如：记录到数据库、发送通知等
        
        # 如果需要异步处理，可以添加到后台任务
        # background_tasks.add_task(process_alert_async, alert_data)
        
        logger.info(f"成功处理 {len(alert_data.get('alerts', []))} 个告警")
        return {"status": "success", "message": "告警已接收"}
        
    except Exception as e:
        logger.error(f"处理告警Webhook失败: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/health")
async def monitoring_health_check():
    """监控系统健康检查"""
    try:
        health_status = {
            "prometheus": False,
            "grafana": False,
            "overall": False
        }
        
        # 检查Prometheus连接
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.PROMETHEUS_URL}/-/healthy")
                health_status["prometheus"] = response.status_code == 200
        except Exception as e:
            logger.warning(f"Prometheus健康检查失败: {e}")
        
        # 检查Grafana连接
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.GRAFANA_URL}/api/health")
                health_status["grafana"] = response.status_code == 200
        except Exception as e:
            logger.warning(f"Grafana健康检查失败: {e}")
        
        # 计算整体状态
        health_status["overall"] = health_status["prometheus"] and health_status["grafana"]
        
        return {
            "status": "healthy" if health_status["overall"] else "unhealthy",
            "checks": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"监控系统健康检查失败: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }