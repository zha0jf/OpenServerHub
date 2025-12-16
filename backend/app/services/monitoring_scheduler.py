import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy import select
# [关键优化] 删除重复定义的 AsyncSessionLocal，使用从 database.py 导入的统一工厂
from ..core.database import AsyncSessionLocal

from ..core.config import settings
from .monitoring import MonitoringService
from ..core.database import async_engine
from ..models.server import Server, ServerStatus, PowerState

logger = logging.getLogger(__name__)

# [关键优化] 删除重复定义的 AsyncSessionLocal，使用从 database.py 导入的统一工厂

class MonitoringSchedulerService:
    """监控数据采集定时任务服务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self._collect_job_id = "monitoring_data_collect"
        self._is_collecting = False
        
        # [核心优化] 限制并发采集数量
        # 防止瞬间创建过多数据库连接导致连接池耗尽
        # 建议值：数据库连接池大小 (pool_size) 的 50% ~ 80%
        self._concurrency_limit = 10 
        self._semaphore = asyncio.Semaphore(self._concurrency_limit)
        
    async def start(self):
        """启动定时任务"""
        if self.is_running:
            logger.warning("监控数据采集定时任务已经运行")
            return
            
        try:
            # 添加定时采集任务
            self.scheduler.add_job(
                self.collect_monitoring_data,
                "interval",
                minutes=settings.MONITORING_INTERVAL,
                id=self._collect_job_id,
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"监控数据采集服务已启动，采集间隔：{settings.MONITORING_INTERVAL}分钟")
            
        except Exception as e:
            logger.error(f"启动监控定时任务失败: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """停止定时任务"""
        if not self.is_running:
            return
            
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("监控数据采集服务已停止")
        except Exception as e:
            logger.error(f"停止监控任务失败: {e}")
            self.is_running = False
    
    async def collect_monitoring_data(self):
        """定时采集所有启用监控的服务器数据"""
        # 防止上一轮任务执行时间过长导致重叠
        if self._is_collecting:
            logger.warning("上一轮监控采集任务尚未完成，跳过本次执行")
            return
            
        try:
            self._is_collecting = True
            start_time = datetime.now()
            logger.debug(f"[监控数据采集] 开始执行监控数据采集任务")
            
            # 1. 快速获取目标服务器ID列表 (只读操作，用完即释放Session)
            db_query_start = datetime.now()
            target_server_ids = []
            async with AsyncSessionLocal() as session:
                # 仅查询 ID，避免加载整个对象导致 Detached 错误
                stmt = select(Server.id).where(
                    Server.status == ServerStatus.ONLINE,
                    Server.power_state == PowerState.ON
                )
                result = await session.execute(stmt)
                target_server_ids = result.scalars().all()
            db_query_time = (datetime.now() - db_query_start).total_seconds()
            logger.debug(f"[监控数据采集] 数据库查询耗时: {db_query_time:.3f}秒")
            
            if not target_server_ids:
                logger.info("当前没有在线且开机的服务器，跳过数据采集")
                return

            logger.info(f"开始采集 {len(target_server_ids)} 台服务器的监控数据")

            # 2. 并发采集 (使用 Semaphore 限制并发)
            tasks = []
            for server_id in target_server_ids:
                # 为每个任务创建协程
                task = asyncio.create_task(self._collect_single_server_safe(server_id))
                tasks.append(task)
            
            # 3. 等待所有任务完成
            # 设置总超时时间，防止任务无限挂起 (假设单台超时30s，计算总缓冲时间)
            # 如果是并发执行，理论最大耗时 = (总数 / 并发数) * 单台超时
            timeout = (len(target_server_ids) // self._concurrency_limit + 2) * 30 + 60
            
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"监控采集任务整体超时 ({timeout}s)，部分数据可能未采集")
                return

            # 统计结果
            success_cnt = sum(1 for r in results if r is True)
            error_cnt = len(target_server_ids) - success_cnt
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"监控采集完成: 成功 {success_cnt}, 失败 {error_cnt}, 耗时 {elapsed:.2f}s")
            logger.debug(f"[监控数据采集] 任务执行完成，总耗时: {elapsed:.3f}秒")
                
        except Exception as e:
            logger.error(f"定时采集监控数据全局异常: {e}")
        finally:
            self._is_collecting = False

    async def _collect_single_server_safe(self, server_id: int) -> bool:
        """
        单个服务器采集包装函数
        包含: 并发控制 + 独立的 Session 管理
        """
        async with self._semaphore:  # 限制并发数
            # [关键] 每个并发任务必须使用独立的 Session，严禁共享 Session
            async with AsyncSessionLocal() as session:
                collect_start = datetime.now()
                try:
                    # 实例化 MonitoringService (传入当前独立的 session)
                    monitoring_service = MonitoringService(session)
                    
                    # 执行采集 (内部包含采集 + 删除旧数据 + 插入新数据)
                    result = await monitoring_service.collect_server_metrics(server_id)
                    
                    collect_time = (datetime.now() - collect_start).total_seconds()
                    if result.get("status") == "success":
                        # 使用 debug 级别，避免日志量过大
                        logger.debug(f"Server {server_id} 采集成功: {len(result.get('collected_metrics', []))} 指标，耗时: {collect_time:.3f}秒")
                        return True
                    else:
                        logger.warning(f"Server {server_id} 采集异常: {result.get('message')}，耗时: {collect_time:.3f}秒")
                        return False
                        
                except Exception as e:
                    logger.error(f"Server {server_id} 采集执行出错: {e}")
                    return False

    def get_status(self) -> Dict[str, Any]:
        """获取定时任务状态"""
        try:
            collect_job = self.scheduler.get_job(self._collect_job_id)
            
            status = {
                "running": self.is_running,
                "monitoring_enabled": settings.MONITORING_ENABLED,
                "collect_job": None
            }
            
            if collect_job:
                status["collect_job"] = {
                    "next_run": collect_job.next_run_time.isoformat() if collect_job.next_run_time else None,
                    "interval_minutes": settings.MONITORING_INTERVAL
                }
                
            return status
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return {"error": str(e)}

# 全局变量
monitoring_scheduler_service: Optional[MonitoringSchedulerService] = None
monitoring_scheduler_service: Optional[MonitoringSchedulerService] = None