import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.server import Server
from app.services.ipmi import IPMIService
from app.services.server_monitoring import PrometheusConfigManager, GrafanaService
from app.core.config import settings

logger = logging.getLogger(__name__)


class ServerMonitoringService:
    """服务器监控服务，处理服务器变更时的监控配置同步"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ipmi_service = IPMIService()
        self.prometheus_manager = PrometheusConfigManager()
        self.grafana_service = GrafanaService(
            settings.GRAFANA_URL,
            settings.GRAFANA_API_KEY
        )
    
    async def on_server_added(self, server: Server) -> bool:
        """服务器添加时的监控配置处理"""
        try:
            # 1. 如果启用了监控，创建openshub用户
            if bool(server.monitoring_enabled):
                await self.ipmi_service.ensure_openshub_user(
                    ip=str(server.ipmi_ip) if server.ipmi_ip is not None else "",
                    admin_username=str(server.ipmi_username) if server.ipmi_username is not None else "",
                    admin_password=str(server.ipmi_password) if server.ipmi_password is not None else "",
                    port=int(str(server.ipmi_port)) if server.ipmi_port is not None else 623
                )
            
            # 2. 同步Prometheus目标配置（仅包含启用监控的服务器）
            servers = self.db.query(Server).filter(Server.monitoring_enabled == True).all()
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            # 3. 不再创建Grafana仪表板，因为前端使用固定的完整IPMI仪表板
            # 保留此注释以备将来可能切换回基于服务器的专用仪表板
            # if bool(server.monitoring_enabled):
            #     await self.grafana_service.create_server_dashboard(server)
            
            logger.info(f"服务器 {server.id} 监控配置已更新")
            return True
        except Exception as e:
            logger.error(f"服务器 {server.id} 监控配置更新失败: {e}")
            return False
    
    async def on_server_deleted(self, server_id: int) -> bool:
        """服务器删除时的监控配置处理"""
        try:
            # 1. 同步Prometheus目标配置（排除已删除的服务器）
            servers = self.db.query(Server).filter(
                Server.monitoring_enabled == True,
                Server.id != server_id
            ).all()
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            # 2. 不再删除Grafana仪表板，因为前端使用固定的完整IPMI仪表板
            # 保留此注释以备将来可能切换回基于服务器的专用仪表板
            
            logger.info(f"服务器 {server_id} 监控配置已清理")
            return True
        except Exception as e:
            logger.error(f"服务器 {server_id} 监控配置清理失败: {e}")
            return False
    
    async def on_server_updated(self, server: Server, original_monitoring_enabled: bool) -> bool:
        """服务器更新时的监控配置处理"""
        try:
            # 如果监控状态从禁用变为启用
            if not original_monitoring_enabled and bool(server.monitoring_enabled):
                # 创建openshub用户
                await self.ipmi_service.ensure_openshub_user(
                    ip=str(server.ipmi_ip) if server.ipmi_ip is not None else "",
                    admin_username=str(server.ipmi_username) if server.ipmi_username is not None else "",
                    admin_password=str(server.ipmi_password) if server.ipmi_password is not None else "",
                    port=int(str(server.ipmi_port)) if server.ipmi_port is not None else 623
                )
                
                # 不再创建Grafana仪表板，因为前端使用固定的完整IPMI仪表板
                # 保留此注释以备将来可能切换回基于服务器的专用仪表板
                # await self.grafana_service.create_server_dashboard(server)
            
            # 如果监控状态发生变化，则同步配置
            servers = self.db.query(Server).filter(Server.monitoring_enabled == True).all()
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            logger.info(f"服务器 {server.id} 监控配置已同步")
            return True
        except Exception as e:
            logger.error(f"服务器 {server.id} 监控配置同步失败: {e}")
            return False