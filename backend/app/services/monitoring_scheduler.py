import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from ..core.config import settings
from .monitoring import MonitoringService
from ..core.database import async_engine
from ..models.server import Server
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

logger = logging.getLogger(__name__)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=async_engine, 
    expire_on_commit=False
)

class MonitoringSchedulerService:
    """监控数据采集定时任务服务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self._collect_job_id = "monitoring_data_collect"
        self._cleanup_job_id = "monitoring_data_cleanup"
        self._is_collecting = False  # 添加标志位，防止任务重叠执行
        
    async def start(self):
        """启动定时任务"""
        if self.is_running:
            logger.warning("监控数据采集定时任务已经运行")
            return
            
        try:
            # 添加定时采集任务，使用配置的时间间隔
            self.scheduler.add_job(
                self.collect_monitoring_data,
                "interval",
                minutes=settings.MONITORING_INTERVAL,  # 使用配置的时间间隔
                id=self._collect_job_id,
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"监控数据采集定时任务服务已启动，采集间隔：{settings.MONITORING_INTERVAL}分钟")
            
        except Exception as e:
            logger.error(f"启动监控数据采集定时任务失败: {e}")
            # 即使启动失败，也要确保状态正确
            self.is_running = False
            raise
    
    async def stop(self):
        """停止定时任务"""
        if not self.is_running:
            logger.info("监控数据采集定时任务服务未运行，无需停止")
            return
            
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("监控数据采集定时任务服务已停止")
        except Exception as e:
            logger.error(f"停止监控数据采集定时任务失败: {e}")
            # 即使停止失败，也要确保状态正确
            self.is_running = False
    
    async def collect_monitoring_data(self):
        """定时采集所有启用监控的服务器数据"""
        # 检查是否已经有任务在运行，防止重叠执行
        if self._is_collecting:
            logger.warning("监控数据采集任务已在运行中，跳过本次执行")
            return
            
        try:
            self._is_collecting = True
            logger.info("开始定时采集所有启用监控的服务器数据")
            
            # 使用异步上下文管理器正确处理会话
            async with AsyncSessionLocal() as session:
                # 获取所有启用监控的服务器
                stmt = select(Server).where(Server.monitoring_enabled == True)
                result = await session.execute(stmt)
                servers = result.scalars().all()
                
                if not servers:
                    logger.info("没有启用监控的服务器，跳过数据采集")
                    return
                
                logger.info(f"找到 {len(servers)} 台启用监控的服务器，开始采集数据")
                
                # 为每台服务器采集数据
                for server in servers:
                    try:
                        monitoring_service = MonitoringService(session)
                        result = await monitoring_service.collect_server_metrics(server.id)
                        
                        if result.get("status") == "success":
                            logger.info(f"成功采集服务器 {server.id} ({server.name}) 的监控数据: {len(result.get('collected_metrics', []))} 个指标")
                        elif result.get("status") == "partial_success":
                            logger.warning(f"部分成功采集服务器 {server.id} ({server.name}) 的监控数据，存在错误: {result.get('errors', [])}")
                        else:
                            logger.error(f"采集服务器 {server.id} ({server.name}) 监控数据失败: {result.get('message', 'Unknown error')}")
                    except Exception as e:
                        logger.error(f"采集服务器 {server.id} ({server.name}) 监控数据时发生异常: {e}")
                
                logger.info("定时采集所有服务器监控数据完成")
                
        except Exception as e:
            logger.error(f"定时采集监控数据失败: {e}")
        finally:
            self._is_collecting = False

    def get_status(self) -> Dict[str, Any]:
        """获取定时任务状态"""
        try:
            collect_job = self.scheduler.get_job(self._collect_job_id)
            
            status: Dict[str, Union[bool, Dict[str, Any]]] = {
                "running": self.is_running,
                "monitoring_enabled": settings.MONITORING_ENABLED,
            }
            
            if collect_job:
                status["collect_job"] = {
                    "job_id": self._collect_job_id,
                    "next_run_time": collect_job.next_run_time.isoformat() if collect_job.next_run_time else None,
                    "interval_minutes": settings.MONITORING_INTERVAL  # 使用配置的时间间隔
                }
                
            return status
        except JobLookupError:
            return {
                "running": self.is_running,
                "monitoring_enabled": settings.MONITORING_ENABLED,
            }
        except Exception as e:
            logger.error(f"获取定时任务状态失败: {e}")
            return {
                "running": self.is_running,
                "monitoring_enabled": settings.MONITORING_ENABLED,
                "error": str(e)
            }


# 创建全局实例
monitoring_scheduler_service = MonitoringSchedulerService()