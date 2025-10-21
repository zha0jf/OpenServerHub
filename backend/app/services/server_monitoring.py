import json
import logging
from typing import List, Optional
import httpx
import os

from sqlalchemy.orm import Session
from app.models.server import Server
from app.core.config import settings

logger = logging.getLogger(__name__)


class PrometheusConfigManager:
    """Prometheus配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        # 通过环境变量或配置文件获取配置路径，如果没有则使用默认值
        self.config_path = config_path or os.getenv("PROMETHEUS_TARGETS_PATH", "/etc/prometheus/targets/ipmi-targets.json")
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
            
            # 写入配置文件到文件系统
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                
                # 写入JSON配置文件
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(targets, f, indent=2, ensure_ascii=False)
                
                logger.info(f"成功写入Prometheus目标配置文件: {self.config_path}")
                logger.debug(f"配置内容: {targets}")
            except Exception as e:
                logger.error(f"写入Prometheus配置文件失败: {e}")
                return False
            
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
    
    def __init__(self, grafana_url: Optional[str] = None, api_key: Optional[str] = None):
        self.grafana_url = grafana_url or settings.GRAFANA_URL
        self.headers = {
            "Authorization": f"Bearer {api_key or settings.GRAFANA_API_KEY}",
            "Content-Type": "application/json"
        }
    
    async def create_server_dashboard(self, server: Server) -> dict:
        """为服务器创建专用监控仪表板"""
        # 获取服务器ID的整数值
        server_id = int(str(server.id))
        
        dashboard_json = {
            "dashboard": {
                "title": f"服务器监控 - {server.name}",
                "tags": ["server", "hardware", "ipmi", f"server-{server_id}"],
                "panels": [
                    self._create_cpu_temperature_panel(server_id),
                    self._create_fan_speed_panel(server_id),
                    self._create_voltage_panel(server_id),
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
                    logger.info(f"Dashboard created for server {server_id}")
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