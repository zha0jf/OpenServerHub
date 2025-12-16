import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from ..core.config import settings
from .ipmi import IPMIService
from ..core.database import async_engine, AsyncSessionLocal  # 导入统一的AsyncSessionLocal
from ..models.server import Server, PowerState, ServerStatus
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy import update, select

logger = logging.getLogger(__name__)

# [关键优化] 删除重复定义的 AsyncSessionLocal，使用从 database.py 导入的统一工厂

class PowerStateSchedulerService:
    """电源状态定时刷新服务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self._refresh_job_id = "power_state_refresh"
        self.ipmi_service = IPMIService()  # 创建IPMI服务实例
        self._is_refreshing = False
        
        # 限制并发数量，防止瞬间创建过多数据库连接导致连接池耗尽
        # 建议值：数据库连接池大小 (pool_size) 的 50% ~ 80%
        self._concurrency_limit = 10  # 降低并发数至10，避免数据库连接池耗尽
        self._semaphore = asyncio.Semaphore(self._concurrency_limit)
        
    async def start(self):
        """启动定时任务"""
        if self.is_running:
            logger.warning("电源状态定时刷新服务已经运行")
            return
            
        try:
            # 添加定时刷新任务
            self.scheduler.add_job(
                self.refresh_all_power_states,
                "interval",
                minutes=settings.POWER_STATE_REFRESH_INTERVAL,
                id=self._refresh_job_id,
                replace_existing=True,
                max_instances=1,  # 防止任务重叠执行
                coalesce=True      # 如果任务积压，只执行最后一次
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"电源状态定时刷新服务已启动，刷新间隔：{settings.POWER_STATE_REFRESH_INTERVAL}分钟")
            
            # 立即执行一次
            asyncio.create_task(self.refresh_all_power_states())
            
        except Exception as e:
            logger.error(f"启动电源状态定时任务失败: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """停止定时任务"""
        if not self.is_running:
            return
            
        try:
            # 关闭IPMI服务，释放资源
            if hasattr(self, 'ipmi_service') and self.ipmi_service:
                self.ipmi_service.close()
            
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("电源状态定时刷新服务已停止")
        except Exception as e:
            logger.error(f"停止电源状态定时任务失败: {e}")
            self.is_running = False
    
    async def refresh_all_power_states(self):
        """刷新所有服务器的电源状态"""
        # 防止上一轮任务执行时间过长导致重叠
        if self._is_refreshing:
            logger.warning("上一轮电源状态刷新任务尚未完成，跳过本次执行")
            return
            
        try:
            self._is_refreshing = True
            start_time = datetime.now()
            logger.debug(f"[电源状态刷新] 开始执行电源状态刷新任务")
            
            # 1. 快速获取所有服务器ID列表 (只读操作，用完即释放Session)
            db_query_start = datetime.now()
            target_server_ids = []
            async with AsyncSessionLocal() as session:
                # 仅查询 ID，避免加载整个对象导致 Detached 错误
                stmt = select(Server.id)
                result = await session.execute(stmt)
                target_server_ids = result.scalars().all()
            db_query_time = (datetime.now() - db_query_start).total_seconds()
            logger.debug(f"[电源状态刷新] 数据库查询耗时: {db_query_time:.3f}秒")
            
            if not target_server_ids:
                logger.info("当前没有服务器，跳过电源状态刷新")
                return

            logger.info(f"开始刷新 {len(target_server_ids)} 台服务器的电源状态")

            # 2. 并发刷新 (使用 Semaphore 限制并发)
            tasks = []
            for server_id in target_server_ids:
                # 为每个任务创建协程
                task = asyncio.create_task(self._refresh_single_server_safe(server_id))
                tasks.append(task)
            
            # 3. 等待所有任务完成
            # 设置总超时时间，防止任务无限挂起 (假设单台超时30s，计算总缓冲时间)
            # 如果是并发执行，理论最大耗时 = (总数 / 并发数) * 单台超时
            timeout = max(30, (len(target_server_ids) / self._concurrency_limit + 1.5) * 30)
            
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"电源状态刷新任务整体超时 ({timeout}s)，部分服务器状态可能未更新")
                return

            # 统计结果
            success_cnt = sum(1 for r in results if r is True)
            error_cnt = len(target_server_ids) - success_cnt
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"电源状态刷新完成: 成功 {success_cnt}, 失败 {error_cnt}, 耗时 {elapsed:.2f}s")
            logger.debug(f"[电源状态刷新] 任务执行完成，总耗时: {elapsed:.3f}秒")
                
        except Exception as e:
            logger.error(f"定时刷新电源状态全局异常: {e}")
        finally:
            self._is_refreshing = False

    async def _refresh_single_server_safe(self, server_id: int) -> bool:
        """
        单个服务器刷新包装函数
        包含: 并发控制 + 独立的 Session 管理 + 异常处理
        """
        async with self._semaphore:  # 限制并发数
            # [关键] 每个并发任务必须使用独立的 Session，严禁共享 Session
            async with AsyncSessionLocal() as session:
                server_fetch_start = datetime.now()
                try:
                    # 1. 获取服务器信息
                    stmt = select(Server).where(Server.id == server_id)
                    result = await session.execute(stmt)
                    server = result.scalar_one_or_none()
                    server_fetch_time = (datetime.now() - server_fetch_start).total_seconds()
                    logger.debug(f"[电源状态刷新] 服务器 {server_id} 信息获取耗时: {server_fetch_time:.3f}秒")
                    
                    if not server:
                        logger.warning(f"服务器不存在 (ID: {server_id})")
                        return False
                    
                    # 2. 调用 IPMI 服务获取电源状态
                    ipmi_start = datetime.now()
                    power_state_str = await self.ipmi_service.get_power_state(
                        ip=server.ipmi_ip,
                        username=server.ipmi_username,
                        password=server.ipmi_password,
                        port=server.ipmi_port
                    )
                    ipmi_time = (datetime.now() - ipmi_start).total_seconds()
                    logger.debug(f"[电源状态刷新] 服务器 {server_id} IPMI调用耗时: {ipmi_time:.3f}秒")
                    
                    # 3. 根据IPMI调用结果确定服务器在线状态和电源状态
                    if power_state_str and power_state_str != "unknown":
                        # IPMI调用成功，服务器在线
                        server_status = ServerStatus.ONLINE
                        
                        # 转换电源状态
                        try:
                            new_power_state = PowerState(power_state_str.lower())
                        except ValueError:
                            logger.warning(f"无效的电源状态值: {power_state_str}")
                            new_power_state = PowerState.UNKNOWN
                    else:
                        # IPMI调用失败，服务器离线，电源状态设为未知
                        server_status = ServerStatus.OFFLINE
                        new_power_state = PowerState.UNKNOWN
                    
                    # 4. 更新数据库
                    db_update_start = datetime.now()
                    stmt = update(Server).where(Server.id == server_id).values(
                        status=server_status,
                        power_state=new_power_state
                    )
                    await session.execute(stmt)
                    await session.commit()
                    db_update_time = (datetime.now() - db_update_start).total_seconds()
                    logger.debug(f"[电源状态刷新] 服务器 {server_id} 数据库更新耗时: {db_update_time:.3f}秒")
                    
                    logger.debug(f"服务器 {server_id} 状态更新成功: 状态={server_status.value}, 电源={new_power_state.value}")
                    return True
                    
                except Exception as e:
                    await session.rollback()
                    logger.error(f"刷新服务器 {server_id} 状态失败: {e}")
                    return False

    def get_status(self) -> Dict[str, Any]:
        """获取定时任务状态"""
        try:
            refresh_job = self.scheduler.get_job(self._refresh_job_id)
            
            status = {
                "running": self.is_running,
                "power_refresh_enabled": settings.POWER_STATE_REFRESH_ENABLED,
                "refresh_job": None
            }
            
            if refresh_job:
                status["refresh_job"] = {
                    "next_run": refresh_job.next_run_time.isoformat() if refresh_job.next_run_time else None,
                    "interval_minutes": settings.POWER_STATE_REFRESH_INTERVAL
                }
                
            return status
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return {"error": str(e)}

# 全局变量
scheduler_service: Optional[PowerStateSchedulerService] = None
