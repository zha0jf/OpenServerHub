import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from ..core.config import settings
from .ipmi import IPMIService
from ..core.database import AsyncSessionLocal
from ..models.server import Server, PowerState, ServerStatus

logger = logging.getLogger(__name__)


class PowerStateSchedulerService:
    """电源状态定时刷新服务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.ipmi_service = IPMIService()
        self.is_running = False
        self._job_id = "power_state_refresh"
        
    async def start(self):
        """启动定时任务"""
        if self.is_running:
            logger.warning("定时任务已经运行")
            return
            
        try:
            # 添加定时任务，每分钟执行一次
            self.scheduler.add_job(
                self.refresh_all_servers_power_state,
                "interval",
                minutes=1,
                id=self._job_id,
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("电源状态定时刷新服务已启动，刷新间隔：1分钟")
            
            # 立即执行一次
            asyncio.create_task(self.refresh_all_servers_power_state())
            
        except Exception as e:
            logger.error(f"启动定时任务失败: {e}")
            raise
    
    async def stop(self):
        """停止定时任务"""
        if not self.is_running:
            return
            
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("电源状态定时刷新服务已停止")
        except Exception as e:
            logger.error(f"停止定时任务失败: {e}")
    
    async def refresh_all_servers_power_state(self):
        """刷新所有服务器的电源状态"""
        try:
            logger.info("开始刷新所有服务器电源状态")
            start_time = datetime.now()
            
            async with AsyncSessionLocal() as session:
                # 获取所有服务器
                from sqlalchemy import select
                result = await session.execute(select(Server))
                servers = result.scalars().all()
                
                if not servers:
                    logger.info("没有需要刷新的服务器")
                    return
                
                logger.info(f"找到 {len(servers)} 台服务器需要刷新电源状态")
                
                # 并发刷新电源状态
                tasks = []
                for server in servers:
                    task = asyncio.create_task(
                        self._refresh_single_server_power_state(server)
                    )
                    tasks.append(task)
                
                # 等待所有任务完成
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 统计结果
                success_count = sum(1 for r in results if r is True)
                failed_count = sum(1 for r in results if r is False)
                error_count = sum(1 for r in results if isinstance(r, Exception))
                
                elapsed_time = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"电源状态刷新完成 - 成功: {success_count}, 失败: {failed_count + error_count}, "
                    f"总计: {len(servers)}, 耗时: {elapsed_time:.2f}秒"
                )
                
        except Exception as e:
            logger.error(f"刷新所有服务器电源状态失败: {e}")
    
    async def _refresh_single_server_power_state(self, server: Server) -> bool:
        """刷新单个服务器的电源状态"""
        try:
            # 获取电源状态
            power_state = await self.ipmi_service.get_power_state(
                ip=server.ipmi_ip,
                username=server.ipmi_username,
                password=server.ipmi_password
            )
            
            if power_state is not None:
                # 转换power_state为枚举类型
                try:
                    power_state_enum = PowerState(power_state.lower())
                except ValueError:
                    power_state_enum = PowerState.UNKNOWN
                
                # 更新数据库中的电源状态
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import update
                    await session.execute(
                        update(Server)
                        .where(Server.id == server.id)
                        .values(power_state=power_state_enum)
                    )
                    await session.commit()
                    
                logger.debug(
                    f"服务器 {server.name} ({server.ipmi_ip}) 电源状态已更新: {power_state_enum.value}"
                )
                return True
            else:
                logger.warning(
                    f"无法获取服务器 {server.name} ({server.ipmi_ip}) 的电源状态"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"刷新服务器 {server.name} ({server.ipmi_ip}) 电源状态失败: {e}"
            )
            
            # 连接失败时更新服务器状态为离线，电源状态为未知
            async with AsyncSessionLocal() as session:
                from sqlalchemy import update
                await session.execute(
                    update(Server)
                    .where(Server.id == server.id)
                    .values(
                        status=ServerStatus.OFFLINE,
                        power_state=PowerState.UNKNOWN
                    )
                )
                await session.commit()
            
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取定时任务状态"""
        try:
            job = self.scheduler.get_job(self._job_id)
            if job:
                return {
                    "running": self.is_running,
                    "job_id": self._job_id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "interval_minutes": 1
                }
            else:
                return {
                    "running": self.is_running,
                    "job_id": self._job_id,
                    "next_run_time": None,
                    "interval_minutes": 1
                }
        except JobLookupError:
            return {
                "running": self.is_running,
                "job_id": self._job_id,
                "next_run_time": None,
                "interval_minutes": 1
            }


# 创建全局实例
scheduler_service = PowerStateSchedulerService()