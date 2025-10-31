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
            # 已删除定时自动采集数据功能
            logger.info("监控数据采集定时任务服务已启动（已禁用自动采集功能）")
            
        except Exception as e:
            logger.error(f"启动监控数据采集定时任务失败: {e}")
            raise
    
    async def stop(self):
        """停止定时任务"""
        if not self.is_running:
            return
            
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("监控数据采集定时任务服务已停止")
        except Exception as e:
            logger.error(f"停止监控数据采集定时任务失败: {e}")
    
    async def cleanup_old_metrics(self):
        """清理旧的监控数据"""
        try:
            logger.info("开始清理旧的监控数据")
            
            # 使用异步上下文管理器正确处理会话
            async with AsyncSessionLocal() as session:
                # 创建监控服务实例
                monitoring_service = MonitoringService(session)
                
                # 清理30天前的监控数据
                deleted_count = monitoring_service.cleanup_old_metrics(30)
                
                logger.info(f"成功清理 {deleted_count} 条旧监控数据")
                
        except Exception as e:
            logger.error(f"清理旧监控数据失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取定时任务状态"""
        try:
            collect_job = self.scheduler.get_job(self._collect_job_id)
            cleanup_job = self.scheduler.get_job(self._cleanup_job_id)
            
            status: Dict[str, Union[bool, Dict[str, Any]]] = {
                "running": self.is_running,
                "monitoring_enabled": settings.MONITORING_ENABLED,
            }
            
            if collect_job:
                status["collect_job"] = {
                    "job_id": self._collect_job_id,
                    "next_run_time": collect_job.next_run_time.isoformat() if collect_job.next_run_time else None,
                    "interval_minutes": settings.MONITORING_INTERVAL if hasattr(settings, 'MONITORING_INTERVAL') else 5
                }
            
            if cleanup_job:
                status["cleanup_job"] = {
                    "job_id": self._cleanup_job_id,
                    "next_run_time": cleanup_job.next_run_time.isoformat() if cleanup_job.next_run_time else None
                }
                
            return status
        except JobLookupError:
            return {
                "running": self.is_running,
                "monitoring_enabled": settings.MONITORING_ENABLED,
            }


# 创建全局实例
monitoring_scheduler_service = MonitoringSchedulerService()