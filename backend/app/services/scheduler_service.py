import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from ..core.config import settings
from .ipmi import IPMIService
from ..core.database import async_engine
from ..models.server import Server, PowerState, ServerStatus
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy import update, select

logger = logging.getLogger(__name__)

# 创建异步会话工厂 - 添加更多配置
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=async_engine, 
    expire_on_commit=False,
    # 添加连接验证配置
    autoflush=False,
    autocommit=False
)

class PowerStateSchedulerService:
    """电源状态定时刷新服务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.ipmi_service = IPMIService()
        self.is_running = False
        self._job_id = "power_state_refresh"
        self._is_refreshing = False  # 添加标志位，防止任务重叠执行
        
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
                minutes=settings.POWER_STATE_REFRESH_INTERVAL,  # 使用配置的间隔
                id=self._job_id,
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"电源状态定时刷新服务已启动，刷新间隔：{settings.POWER_STATE_REFRESH_INTERVAL}分钟")
            
            # 立即执行一次
            asyncio.create_task(self.refresh_all_servers_power_state())
            
        except Exception as e:
            logger.error(f"启动定时任务失败: {e}")
            # 即使启动失败，也要确保状态正确
            self.is_running = False
            raise
    
    async def stop(self):
        """停止定时任务"""
        if not self.is_running:
            logger.info("电源状态定时刷新服务未运行，无需停止")
            return
            
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("电源状态定时刷新服务已停止")
        except Exception as e:
            logger.error(f"停止定时任务失败: {e}")
            # 即使停止失败，也要确保状态正确
            self.is_running = False
    
    async def refresh_all_servers_power_state(self):
        """刷新所有服务器的电源状态"""
        # 检查是否已经有任务在运行，防止重叠执行
        if self._is_refreshing:
            logger.warning("电源状态刷新任务已在运行中，跳过本次执行")
            return
            
        try:
            self._is_refreshing = True  # 设置标志位
            logger.info("开始刷新所有服务器电源状态")
            start_time = datetime.now()
            
            # 使用异步上下文管理器正确处理会话
            async with AsyncSessionLocal() as session:
                # 获取所有服务器
                stmt = select(Server)
                result = await session.execute(stmt)
                servers = result.scalars().all()
                
                if not servers:
                    logger.info("没有需要刷新的服务器")
                    return
                
                logger.info(f"找到 {len(servers)} 台服务器需要刷新电源状态")
                
                # 并发刷新电源状态，但限制并发数量以避免资源耗尽
                semaphore = asyncio.Semaphore(20)  # 限制并发数为20
                
                async def refresh_with_semaphore(server):
                    async with semaphore:
                        return await self._refresh_single_server_power_state(server)
                
                # 并发刷新电源状态
                tasks = []
                for server in servers:
                    task = asyncio.create_task(refresh_with_semaphore(server))
                    tasks.append(task)
                
                # 等待所有任务完成，设置超时以防止任务无限期挂起
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=len(servers) * 10  # 设置超时时间为服务器数量*10秒
                    )
                except asyncio.TimeoutError:
                    logger.error("电源状态刷新任务超时")
                    return
                except asyncio.CancelledError:
                    logger.warning("电源状态刷新任务被取消")
                    return
                
                # 统计结果
                success_count = sum(1 for r in results if r is True)
                failed_count = sum(1 for r in results if r is False)
                error_count = sum(1 for r in results if isinstance(r, Exception))
                
                elapsed_time = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"电源状态刷新完成 - 成功: {success_count}, 失败: {failed_count + error_count}, "
                    f"总计: {len(servers)}, 耗时: {elapsed_time:.2f}秒"
                )
                
        except asyncio.CancelledError:
            logger.warning("电源状态刷新任务被取消")
        except Exception as e:
            logger.error(f"刷新所有服务器电源状态失败: {e}")
        finally:
            self._is_refreshing = False  # 重置标志位
    
    async def _refresh_single_server_power_state(self, server: Server) -> bool:
        """刷新单个服务器的电源状态"""
        try:
            # 获取电源状态（确保传递正确的类型）
            # 从数据库模型中提取值并转换为正确的类型
            ip = str(server.ipmi_ip) if server.ipmi_ip is not None else ""
            username = str(server.ipmi_username) if server.ipmi_username is not None else ""
            password = str(server.ipmi_password) if server.ipmi_password is not None else ""
            
            # 处理端口，确保是整数类型
            port = 623  # 默认端口
            if server.ipmi_port is not None:
                try:
                    # 尝试转换为整数，如果失败则使用默认值
                    port = int(str(server.ipmi_port))
                except (ValueError, TypeError):
                    port = 623
            
            power_state = await self.ipmi_service.get_power_state(
                ip=ip,
                username=username,
                password=password,
                port=port
            )
            
            if power_state is not None:
                # 转换power_state为枚举类型
                try:
                    power_state_enum = PowerState(power_state.lower())
                except ValueError:
                    power_state_enum = PowerState.UNKNOWN
                
                # 根据电源状态确定BMC状态
                # 如果电源状态检测成功，说明BMC是在线的
                bmc_status = ServerStatus.ONLINE
                
                # 更新数据库中的电源状态和BMC状态
                try:
                    async with AsyncSessionLocal() as session:
                        stmt = update(Server).where(Server.id == server.id).values(
                            power_state=power_state_enum,
                            status=bmc_status,
                            last_seen=datetime.utcnow()
                        )
                        await session.execute(stmt)
                        await session.commit()
                        
                    logger.debug(
                        f"服务器 {server.name} ({server.ipmi_ip}) 电源状态已更新: {power_state_enum.value}, "
                        f"BMC状态已更新: {bmc_status.value}"
                    )
                    return True
                except (SQLAlchemyError, DisconnectionError) as db_error:
                    logger.error(
                        f"更新服务器 {server.name} ({server.ipmi_ip}) 数据库状态失败: {db_error}"
                    )
                    # 尝试重新建立连接后重试一次
                    try:
                        async with AsyncSessionLocal() as session:
                            stmt = update(Server).where(Server.id == server.id).values(
                                power_state=power_state_enum,
                                status=bmc_status,
                                last_seen=datetime.utcnow()
                            )
                            await session.execute(stmt)
                            await session.commit()
                            
                        logger.debug(
                            f"服务器 {server.name} ({server.ipmi_ip}) 电源状态已更新（重试成功）: {power_state_enum.value}"
                        )
                        return True
                    except Exception as retry_error:
                        logger.error(
                            f"重试更新服务器 {server.name} ({server.ipmi_ip}) 数据库状态失败: {retry_error}"
                        )
                        return False
                except Exception as e:
                    logger.error(
                        f"更新服务器 {server.name} ({server.ipmi_ip}) 数据库状态时发生未知错误: {e}"
                    )
                    return False
                    
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
            try:
                async with AsyncSessionLocal() as session:
                    stmt = update(Server).where(Server.id == server.id).values(
                        status=ServerStatus.OFFLINE,
                        power_state=PowerState.UNKNOWN
                    )
                    await session.execute(stmt)
                    await session.commit()
            except (SQLAlchemyError, DisconnectionError) as db_error:
                logger.error(
                    f"更新服务器 {server.name} ({server.ipmi_ip}) 离线状态失败: {db_error}"
                )
                # 尝试重新建立连接后重试一次
                try:
                    async with AsyncSessionLocal() as session:
                        stmt = update(Server).where(Server.id == server.id).values(
                            status=ServerStatus.OFFLINE,
                            power_state=PowerState.UNKNOWN
                        )
                        await session.execute(stmt)
                        await session.commit()
                    logger.debug(
                        f"服务器 {server.name} ({server.ipmi_ip}) 离线状态已更新（重试成功）"
                    )
                except Exception as retry_error:
                    logger.error(
                        f"重试更新服务器 {server.name} ({server.ipmi_ip}) 离线状态失败: {retry_error}"
                    )
            except Exception as update_error:
                logger.error(
                    f"更新服务器 {server.name} ({server.ipmi_ip}) 离线状态时发生未知错误: {update_error}"
                )
            
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
                    "interval_minutes": settings.POWER_STATE_REFRESH_INTERVAL
                }
            else:
                return {
                    "running": self.is_running,
                    "job_id": self._job_id,
                    "next_run_time": None,
                    "interval_minutes": settings.POWER_STATE_REFRESH_INTERVAL
                }
        except JobLookupError:
            return {
                "running": self.is_running,
                "job_id": self._job_id,
                "next_run_time": None,
                "interval_minutes": settings.POWER_STATE_REFRESH_INTERVAL
            }
        except Exception as e:
            logger.error(f"获取定时任务状态失败: {e}")
            return {
                "running": self.is_running,
                "job_id": self._job_id,
                "next_run_time": None,
                "interval_minutes": settings.POWER_STATE_REFRESH_INTERVAL,
                "error": str(e)
            }
    
    def schedule_server_refresh(self, server_id: int):
        """
        为特定服务器调度刷新任务，在1秒和4秒后执行两次刷新
        :param server_id: 服务器ID
        """
        # 生成唯一的任务ID
        job_id_base = f"server_refresh_{server_id}"
        
        # 先移除可能存在的旧任务
        try:
            self.scheduler.remove_job(job_id_base + "_1")
        except JobLookupError:
            pass  # 任务不存在，忽略错误
        
        try:
            self.scheduler.remove_job(job_id_base + "_2")
        except JobLookupError:
            pass  # 任务不存在，忽略错误
        
        # 添加第一次刷新任务（1秒后执行）
        self.scheduler.add_job(
            self._execute_single_server_refresh,
            'date',
            run_date=datetime.now() + timedelta(seconds=1),
            id=job_id_base + "_1",
            replace_existing=True,
            args=[server_id]
        )
        
        # 添加第二次刷新任务（4秒后执行）
        self.scheduler.add_job(
            self._execute_single_server_refresh,
            'date',
            run_date=datetime.now() + timedelta(seconds=4),
            id=job_id_base + "_2",
            replace_existing=True,
            args=[server_id]
        )
        
        logger.info(f"已为服务器 {server_id} 调度刷新任务，在1秒和4秒后分别执行刷新")
    
    def schedule_single_refresh(self, server_id: int, delay: float = 0.5):
        """
        为特定服务器调度单次刷新任务
        :param server_id: 服务器ID
        :param delay: 延迟时间（秒），默认0.5秒
        """
        # 生成唯一的任务ID
        job_id = f"single_refresh_{server_id}"
        
        # 先移除可能存在的旧任务
        try:
            self.scheduler.remove_job(job_id)
        except JobLookupError:
            pass  # 任务不存在，忽略错误
        
        # 添加刷新任务
        self.scheduler.add_job(
            self._execute_single_server_refresh,
            'date',
            run_date=datetime.now() + timedelta(seconds=delay),
            id=job_id,
            replace_existing=True,
            args=[server_id]
        )
        
        logger.info(f"已为服务器 {server_id} 调度单次刷新任务，在 {delay} 秒后执行")
    
    async def _execute_single_server_refresh(self, server_id: int):
        """
        执行单个服务器的电源状态刷新
        :param server_id: 服务器ID
        """
        try:
            logger.info(f"开始刷新服务器 {server_id} 的电源状态")
            
            # 使用异步上下文管理器正确处理会话
            async with AsyncSessionLocal() as session:
                # 获取指定服务器
                stmt = select(Server).where(Server.id == server_id)
                result = await session.execute(stmt)
                server = result.scalar_one_or_none()
                
                if not server:
                    logger.warning(f"未找到ID为 {server_id} 的服务器")
                    return
                
                # 刷新服务器电源状态
                success = await self._refresh_single_server_power_state(server)
                
                if success:
                    logger.info(f"服务器 {server_id} 电源状态刷新成功")
                else:
                    logger.warning(f"服务器 {server_id} 电源状态刷新失败")
                    
        except Exception as e:
            logger.error(f"刷新服务器 {server_id} 电源状态时发生错误: {e}")