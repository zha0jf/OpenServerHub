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
            # 添加监控数据采集任务
            if settings.MONITORING_ENABLED:
                self.scheduler.add_job(
                    self.collect_all_servers_metrics,
                    "interval",
                    minutes=settings.MONITORING_INTERVAL if hasattr(settings, 'MONITORING_INTERVAL') else 5,  # 默认5分钟采集一次
                    id=self._collect_job_id,
                    replace_existing=True,
                    max_instances=1,
                    coalesce=True
                )
                
                # 添加监控数据清理任务（每天凌晨2点执行）
                self.scheduler.add_job(
                    self.cleanup_old_metrics,
                    "cron",
                    hour=2,
                    minute=0,
                    id=self._cleanup_job_id,
                    replace_existing=True,
                    max_instances=1
                )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("监控数据采集定时任务服务已启动")
            if settings.MONITORING_ENABLED:
                logger.info(f"监控数据采集间隔：{settings.MONITORING_INTERVAL if hasattr(settings, 'MONITORING_INTERVAL') else 5}分钟")
            
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
    
    async def collect_all_servers_metrics(self):
        """采集所有服务器的监控数据"""
        # 检查是否已经有任务在运行，防止重叠执行
        if self._is_collecting:
            logger.warning("监控数据采集任务已在运行中，跳过本次执行")
            return
            
        if not settings.MONITORING_ENABLED:
            logger.debug("监控功能未启用，跳过数据采集")
            return
            
        try:
            self._is_collecting = True  # 设置标志位
            logger.info("开始采集所有服务器监控数据")
            start_time = datetime.now()
            
            # 使用异步上下文管理器正确处理会话
            async with AsyncSessionLocal() as session:
                # 获取所有启用监控的服务器
                stmt = select(Server).where(Server.monitoring_enabled == True)
                result = await session.execute(stmt)
                servers = result.scalars().all()
                
                if not servers:
                    logger.info("没有需要采集监控数据的服务器")
                    return
                
                logger.info(f"找到 {len(servers)} 台启用监控的服务器需要采集数据")
                
                # 并发采集监控数据，但限制并发数量以避免资源耗尽
                semaphore = asyncio.Semaphore(10)  # 限制并发数为10
                
                async def collect_with_semaphore(server):
                    async with semaphore:
                        return await self._collect_single_server_metrics(session, server)
                
                # 并发采集监控数据
                tasks = []
                for server in servers:
                    task = asyncio.create_task(collect_with_semaphore(server))
                    tasks.append(task)
                
                # 等待所有任务完成，设置超时以防止任务无限期挂起
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=len(servers) * 30  # 设置超时时间为服务器数量*30秒
                    )
                except asyncio.TimeoutError:
                    logger.error("监控数据采集任务超时")
                    return
                
                # 统计结果
                success_count = sum(1 for r in results if r is True)
                failed_count = sum(1 for r in results if r is False)
                error_count = sum(1 for r in results if isinstance(r, Exception))
                
                elapsed_time = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"监控数据采集完成 - 成功: {success_count}, 失败: {failed_count + error_count}, "
                    f"总计: {len(servers)}, 耗时: {elapsed_time:.2f}秒"
                )
                
        except Exception as e:
            logger.error(f"采集所有服务器监控数据失败: {e}")
        finally:
            self._is_collecting = False  # 重置标志位
    
    async def _collect_single_server_metrics(self, session: AsyncSession, server: Server) -> bool:
        """采集单个服务器的监控数据"""
        try:
            # 创建监控服务实例
            monitoring_service = MonitoringService(session)
            
            # 采集监控数据
            result = await monitoring_service.collect_server_metrics(server.id)
            
            if result.get("status") == "success":
                logger.debug(
                    f"服务器 {server.name} ({server.ipmi_ip}) 监控数据采集成功: "
                    f"{len(result.get('collected_metrics', []))} 个指标"
                )
                return True
            elif result.get("status") == "partial_success":
                logger.warning(
                    f"服务器 {server.name} ({server.ipmi_ip}) 监控数据部分采集成功，存在错误: "
                    f"{result.get('errors', [])}"
                )
                return True
            else:
                logger.error(
                    f"服务器 {server.name} ({server.ipmi_ip}) 监控数据采集失败: "
                    f"{result.get('message', 'Unknown error')}"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"采集服务器 {server.name} ({server.ipmi_ip}) 监控数据失败: {e}"
            )
            return False
    
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