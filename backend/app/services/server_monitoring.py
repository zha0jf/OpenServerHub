import json
import logging
from typing import List
import httpx

from sqlalchemy.orm import Session
from app.models.server import Server
from app.core.config import settings

logger = logging.getLogger(__name__)


class PrometheusConfigManager:
    """Prometheus配置管理器"""
    
    def __init__(self, config_path: str = "/etc/prometheus/targets/ipmi-targets.json"):
        self.config_path = config_path
        self.reload_url = f"{settings.PROMETHEUS_URL}/-/reload"
    
    async def sync_ipmi_targets(self, servers: List[Server]) -> bool:
        """根据服务器列表同步IPMI监控目标"""
        try:
            # 生成目标配置
            targets = []
            for server in servers:
                # 假设所有服务器都需要监控，实际可以根据server.monitoring_enabled字段判断
                target = {
                    "targets": [f"{server.ipmi_ip}:9290"],
                    "labels": {
                        "server_id": str(server.id),
                        "server_name": server.name,
                        "ipmi_ip": server.ipmi_ip,
                        "manufacturer": server.manufacturer or "unknown"
                    }
                }
                targets.append(target)
            
            # 写入配置文件（在实际实现中，这里需要写入到文件系统）
            config_data = targets
            logger.info(f"Syncing Prometheus targets: {config_data}")
            
            # 通知Prometheus重新加载配置
            await self.reload_prometheus()
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync Prometheus config: {e}")
            return False
    
    async def reload_prometheus(self) -> bool:
        """通知Prometheus重新加载配置"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.reload_url)
                if response.status_code == 200:
                    logger.info("Prometheus config reloaded successfully")
                    return True
                else:
                    logger.error(f"Failed to reload Prometheus config: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Failed to reload Prometheus: {e}")
            return False


class GrafanaService:
    """Grafana服务"""
    
    def __init__(self, grafana_url: str = None, api_key: str = None):
        self.grafana_url = grafana_url or settings.GRAFANA_URL
        self.headers = {
            "Authorization": f"Bearer {api_key or settings.GRAFANA_API_KEY}",
            "Content-Type": "application/json"
        }
    
    async def create_server_dashboard(self, server: Server) -> dict:
        """为服务器创建专用监控仪表板"""
        dashboard_json = {
            "dashboard": {
                "title": f"服务器监控 - {server.name}",
                "tags": ["server", "hardware", "ipmi", f"server-{server.id}"],
                "panels": [
                    self._create_cpu_temperature_panel(server.id),
                    self._create_fan_speed_panel(server.id),
                    self._create_voltage_panel(server.id),
                ]
            },
            "overwrite": True
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.grafana_url}/api/dashboards/db",
                    headers=self.headers,
                    json=dashboard_json
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Dashboard created for server {server.id}")
                    return {
                        "success": True,
                        "dashboard_uid": result['uid'],
                        "dashboard_url": f"{self.grafana_url}/d/{result['uid']}"
                    }
                else:
                    logger.error(f"Grafana API error: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"Grafana API error: {response.status_code}"
                    }
        except Exception as e:
            logger.error(f"Failed to create Grafana dashboard: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_cpu_temperature_panel(self, server_id: int):
        """创建CPU温度面板"""
        return {
            "title": "CPU温度",
            "type": "timeseries",
            "datasource": "Prometheus",
            "targets": [
                {
                    "expr": f'ipmi_temperature_celsius{{server_id="{server_id}",name=~".*CPU.*"}}',
                    "legendFormat": "{{name}}",
                    "refId": "A"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": "celsius",
                    "min": 0,
                    "max": 100
                }
            }
        }
    
    def _create_fan_speed_panel(self, server_id: int):
        """创建风扇转速面板"""
        return {
            "title": "风扇转速",
            "type": "timeseries",
            "datasource": "Prometheus",
            "targets": [
                {
                    "expr": f'ipmi_fan_speed_rpm{{server_id="{server_id}"}}',
                    "legendFormat": "{{name}}",
                    "refId": "A"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": "rpm"
                }
            }
        }
    
    def _create_voltage_panel(self, server_id: int):
        """创建电压面板"""
        return {
            "title": "电压",
            "type": "timeseries",
            "datasource": "Prometheus",
            "targets": [
                {
                    "expr": f'ipmi_voltage_volts{{server_id="{server_id}"}}',
                    "legendFormat": "{{name}}",
                    "refId": "A"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": "volt"
                }
            }
        }


class ServerMonitoringService:
    """服务器监控服务，处理服务器变更时的监控配置同步"""
    
    def __init__(self, db: Session):
        self.db = db
        self.prometheus_manager = PrometheusConfigManager()
        self.grafana_service = GrafanaService()
    
    async def on_server_added(self, server: Server) -> bool:
        """服务器添加时的监控配置处理"""
        try:
            # 1. 同步Prometheus目标配置
            servers = self.db.query(Server).all()
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            # 2. 为新服务器创建Grafana仪表板
            await self.grafana_service.create_server_dashboard(server)
            
            logger.info(f"服务器 {server.id} 监控配置已更新")
            return True
        except Exception as e:
            logger.error(f"服务器 {server.id} 监控配置更新失败: {e}")
            return False
    
    async def on_server_deleted(self, server_id: int) -> bool:
        """服务器删除时的监控配置处理"""
        try:
            # 1. 同步Prometheus目标配置
            servers = self.db.query(Server).all()
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            # 2. 可以选择删除对应的Grafana仪表板
            
            logger.info(f"服务器 {server_id} 监控配置已清理")
            return True
        except Exception as e:
            logger.error(f"服务器 {server_id} 监控配置清理失败: {e}")
            return False
    
    async def on_server_updated(self, server: Server) -> bool:
        """服务器更新时的监控配置处理"""
        try:
            # 同步Prometheus目标配置
            servers = self.db.query(Server).all()
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            logger.info(f"服务器 {server.id} 监控配置已同步")
            return True
        except Exception as e:
            logger.error(f"服务器 {server.id} 监控配置同步失败: {e}")
            return False