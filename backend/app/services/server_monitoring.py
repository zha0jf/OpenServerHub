import json
import logging
from typing import List, Optional
import httpx
import os
import base64

from sqlalchemy.orm import Session
from app.models.server import Server
from app.core.config import settings

logger = logging.getLogger(__name__)


class PrometheusConfigManager:
    """Prometheus配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        # 通过环境变量或配置文件获取配置路径，如果没有则使用默认值
        default_path = "/etc/prometheus/targets/ipmi-targets.json"
        self.config_path = config_path or settings.PROMETHEUS_TARGETS_PATH or default_path
        self.reload_url = f"{settings.PROMETHEUS_URL}/-/reload"
        
        # 记录初始化信息
        logger.debug(f"PrometheusConfigManager初始化完成")
        logger.debug(f"配置文件路径: {self.config_path}")
        logger.debug(f"Prometheus重载URL: {self.reload_url}")
    
    async def sync_ipmi_targets(self, servers: List[Server]) -> bool:
        """根据服务器列表同步IPMI监控目标"""
        logger.info(f"开始同步Prometheus IPMI目标配置，服务器数量: {len(servers)}")
        logger.debug(f"服务器列表详情: {[{'id': s.id, 'name': s.name, 'ipmi_ip': s.ipmi_ip} for s in servers]}")
        
        try:
            # 生成目标配置 - 为IPMI Exporter生成正确的配置格式
            targets = []
            for server in servers:
                # 处理可能为None的字段，确保转换为字符串
                ipmi_ip = str(server.ipmi_ip) if server.ipmi_ip is not None else ""
                manufacturer = str(server.manufacturer) if server.manufacturer is not None else "unknown"
                
                # 为每个服务器生成IPMI Exporter配置
                # 正确的配置应该是让Prometheus连接IPMI Exporter容器，而不是直接连接目标服务器
                target = {
                    "targets": ["ipmi-exporter:9290"],  # IPMI Exporter服务地址
                    "labels": {
                        "server_id": str(server.id),
                        "server_name": str(server.name),
                        "module": "remote",  # 指定使用remote模块
                        "ipmi_ip": ipmi_ip,
                        "manufacturer": manufacturer,
                        "__param_target": ipmi_ip  # 目标服务器IPMI地址作为参数传递
                        # 移除用户名、密码、端口、权限等参数
                    }
                }
                
                # 记录每个服务器的配置详情（调试模式）
                logger.debug(f"服务器 {server.name} (ID: {server.id}) 的监控配置: {target}")
                targets.append(target)
            
            logger.info(f"生成监控目标配置完成，共 {len(targets)} 个目标")
            
            # 写入配置文件到文件系统
            try:
                # 确保目录存在
                config_dir = os.path.dirname(self.config_path)
                os.makedirs(config_dir, exist_ok=True)
                logger.debug(f"确保配置目录存在: {config_dir}")
                
                # 写入JSON配置文件
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(targets, f, indent=2, ensure_ascii=False)
                
                logger.info(f"成功写入Prometheus目标配置文件: {self.config_path}")
                logger.debug(f"配置内容: {targets}")
                
                # 验证文件是否成功写入
                if os.path.exists(self.config_path):
                    file_size = os.path.getsize(self.config_path)
                    logger.debug(f"配置文件大小: {file_size} 字节")
                else:
                    logger.error(f"配置文件写入失败，文件不存在: {self.config_path}")
                    return False
                    
            except Exception as e:
                logger.error(f"写入Prometheus配置文件失败: {e}")
                logger.exception(e)  # 记录完整的异常堆栈
                return False
            
            # 通知Prometheus重新加载配置
            reload_result = await self.reload_prometheus()
            if reload_result:
                logger.info("Prometheus配置同步和重载完成")
            else:
                logger.warning("Prometheus配置同步完成，但重载失败")
                
            return True
            
        except Exception as e:
            logger.error(f"同步Prometheus配置失败: {e}")
            logger.exception(e)  # 记录完整的异常堆栈
            return False
    
    async def reload_prometheus(self) -> bool:
        """通知Prometheus重新加载配置"""
        logger.debug(f"开始通知Prometheus重新加载配置: {self.reload_url}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.reload_url)
                logger.debug(f"Prometheus重载响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info("Prometheus配置重载成功")
                    return True
                else:
                    logger.error(f"Prometheus配置重载失败，状态码: {response.status_code}")
                    logger.debug(f"响应内容: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Prometheus重载请求失败: {e}")
            logger.exception(e)  # 记录完整的异常堆栈
            return False


class GrafanaService:
    """Grafana服务"""
    
    def __init__(self, grafana_url: Optional[str] = None, api_key: Optional[str] = None):
        self.grafana_url = grafana_url or settings.GRAFANA_URL
        # 检查是否使用默认的API密钥占位符
        grafana_api_key = api_key or settings.GRAFANA_API_KEY
        if grafana_api_key == "your-grafana-api-key-here":
            # 如果是默认占位符，使用基本认证（admin:admin）
            auth_string = "admin:admin"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            self.headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json"
            }
        else:
            # 否则使用API密钥认证
            self.headers = {
                "Authorization": f"Bearer {grafana_api_key}",
                "Content-Type": "application/json"
            }
        logger.debug(f"GrafanaService初始化完成")
        logger.debug(f"Grafana URL: {self.grafana_url}")
    
    async def create_server_dashboard(self, server: Server) -> dict:
        """为服务器创建专用监控仪表板"""
        logger.info(f"开始为服务器 {server.name} (ID: {server.id}) 创建Grafana仪表板")
        
        # 获取服务器ID的整数值
        server_id = int(str(server.id))
        
        # 使用固定的仪表板UID格式，与前端保持一致
        dashboard_uid = f"server-dashboard-{server_id}"
        
        dashboard_json = {
            "dashboard": {
                "id": None,
                "uid": dashboard_uid,
                "title": f"服务器监控 - {server.name}",
                "tags": ["server", "hardware", "ipmi", f"server-{server_id}"],
                "timezone": "browser",
                "schemaVersion": 16,
                "version": 0,
                "refresh": "30s",
                "panels": [
                    self._create_cpu_temperature_panel(server_id),
                    self._create_fan_speed_panel(server_id),
                    self._create_voltage_panel(server_id),
                ]
            },
            "overwrite": True,
            "message": f"为服务器 {server.name} (ID: {server_id}) 自动创建仪表板"
        }
        
        logger.debug(f"准备创建仪表板，服务器ID: {server_id}")
        logger.debug(f"仪表板配置: {dashboard_json}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.grafana_url}/api/dashboards/db",
                    headers=self.headers,
                    json=dashboard_json
                )
                
                logger.debug(f"Grafana API响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"服务器 {server_id} 的Grafana仪表板创建成功")
                    logger.debug(f"仪表板详情: {result}")
                    return {
                        "success": True,
                        "dashboard_uid": result.get('uid', dashboard_uid),
                        "dashboard_url": f"{self.grafana_url}/d/{result.get('uid', dashboard_uid)}"
                    }
                else:
                    logger.error(f"Grafana API错误，状态码: {response.status_code}")
                    logger.debug(f"响应内容: {response.text}")
                    # 即使API调用失败，也返回默认的仪表板信息
                    return {
                        "success": False,
                        "dashboard_uid": dashboard_uid,
                        "dashboard_url": f"{self.grafana_url}/d/{dashboard_uid}",
                        "error": f"Grafana API error: {response.status_code}"
                    }
        except Exception as e:
            logger.error(f"创建Grafana仪表板失败: {e}")
            logger.exception(e)  # 记录完整的异常堆栈
            # 即使创建失败，也返回默认的仪表板信息
            return {
                "success": False,
                "dashboard_uid": dashboard_uid,
                "dashboard_url": f"{self.grafana_url}/d/{dashboard_uid}",
                "error": str(e)
            }
    
    def _create_cpu_temperature_panel(self, server_id: int):
        """创建CPU温度面板"""
        logger.debug(f"创建CPU温度面板，服务器ID: {server_id}")
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
        logger.debug(f"创建风扇转速面板，服务器ID: {server_id}")
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
        logger.debug(f"创建电压面板，服务器ID: {server_id}")
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