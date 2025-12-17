import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.server import Server
from app.services.ipmi import IPMIService
from app.services.server_monitoring import PrometheusConfigManager, GrafanaService
from app.core.config import settings

logger = logging.getLogger(__name__)


class ServerMonitoringService:
    """服务器监控服务，处理服务器变更时的监控配置同步"""
    
    def __init__(self, db: AsyncSession):
        # [修改点 1] 类型提示改为 AsyncSession
        self.db = db
        # 注意：如果 IPMIService 初始化开销很大（创建线程池），
        # 建议将其作为依赖注入传入，而不是在这里每次 new 一个
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
                    port=int(str(server.ipmi_port)) if server.ipmi_port is not None else settings.IPMI_DEFAULT_PORT
                )
            
            # 2. 同步Prometheus目标配置（仅包含启用监控的服务器）
            # [修改点 2] 使用异步查询语法
            stmt = select(Server).where(Server.monitoring_enabled == True)
            result = await self.db.execute(stmt)
            servers = result.scalars().all()
            
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            logger.info(f"服务器 {server.id} 监控配置已更新")
            return True
        except Exception as e:
            logger.error(f"服务器 {server.id} 监控配置更新失败: {e}")
            return False
    
    async def on_server_deleted(self, server_id: int) -> bool:
        """服务器删除时的监控配置处理"""
        try:
            # 1. 同步Prometheus目标配置（排除已删除的服务器）
            # [修改点 3] 使用异步查询语法
            stmt = select(Server).where(
                Server.monitoring_enabled == True,
                Server.id != server_id
            )
            result = await self.db.execute(stmt)
            servers = result.scalars().all()
            
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
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
                    port=int(str(server.ipmi_port)) if server.ipmi_port is not None else settings.IPMI_DEFAULT_PORT
                )
            
            # 如果监控状态发生变化，则同步配置
            # [修改点 4] 使用异步查询语法
            stmt = select(Server).where(Server.monitoring_enabled == True)
            result = await self.db.execute(stmt)
            servers = result.scalars().all()
            
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            logger.info(f"服务器 {server.id} 监控配置已同步")
            return True
        except Exception as e:
            logger.error(f"服务器 {server.id} 监控配置同步失败: {e}")
            return False