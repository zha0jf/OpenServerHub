import asyncio
import logging
import socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, update

# 请根据实际项目路径调整导入
from ..core.config import settings
from ..core.database import AsyncSessionLocal
from ..models.server import Server, ServerStatus

logger = logging.getLogger(__name__)

# ==============================================================================
# IPMI 探测协议 Payload 定义
# ==============================================================================

# 1. IPMI v2.0 (RMCP+) - Get Channel Authentication Capabilities
# 适用于: OpenBMC, Dell iDRAC 7/8/9, HP iLO 4/5, Lenovo XCC 等现代设备
# 即使未提供账号密码，BMC 也会回复支持的加密算法列表。
PAYLOAD_V2 = bytes.fromhex("0600ff07000000000000000000092018c88100388e04b5")

# 2. IPMI v1.5 (ASF) - Presence Ping
# 适用于: 2010年以前的老旧服务器 (Supermicro IPMI 1.5 等)
# 现代设备可能会忽略此包，因此需要与 V2 包混合发送。
PAYLOAD_V1_5 = bytes.fromhex("0600ff06000011be803f10020001050000000000")

# ==============================================================================

class OfflineServerCheckerService:
    """
    离线服务器定时检查服务 (Hybrid UDP Probe)
    特性:
    - 兼容 IPMI v1.5 / v2.0 / OpenBMC
    - 私有线程池资源隔离
    - 智能超时重试机制
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self._check_job_id = "offline_server_check"
        self._is_checking = False
        
        # [资源管理] 持有后台任务引用，防止被 Python GC 提前回收导致任务中断
        self._initial_task = None

        # --- 配置加载 ---
        # 1. 并发数配置
        self._max_workers = settings.OFFLINE_SERVER_WORKER_COUNT
        
        # 2. 超时配置 (单位: 秒, 如果未配置则默认 3.0 秒)
        self._total_timeout = getattr(settings, "SERVER_ONLINE_CHECK_TIMEOUT", 3.0)

        # --- 资源初始化 ---
        # 3. 创建私有线程池 (关键: 资源隔离，避免阻塞主进程的默认线程池)
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers, 
            thread_name_prefix="ipmi_checker"
        )
        
        # 4. 信号量限制 (确保并发 Socket 请求数不超过线程池大小)
        self._connectivity_semaphore = asyncio.Semaphore(self._max_workers)

    async def start(self):
        """启动定时任务"""
        if self.is_running:
            logger.warning("离线服务器检查服务已经运行")
            return

        try:
            # [规范修复] 使用 get_running_loop 替代 get_event_loop
            loop = asyncio.get_running_loop()

            self.scheduler.add_job(
                self.check_offline_servers,
                "interval",
                minutes=settings.OFFLINE_SERVER_CHECK_INTERVAL,
                id=self._check_job_id,
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )

            self.scheduler.start()
            self.is_running = True
            
            logger.info(
                f"离线服务器检查服务已启动 | 协议: Hybrid(v1.5+v2.0) | 并发: {self._max_workers} | "
                f"超时预算: {self._total_timeout}s"
            )

            # [安全规范修复] 
            # 1. 使用 loop.create_task 明确上下文
            # 2. 将任务赋值给实例变量，防止被垃圾回收(GC)
            self._initial_task = loop.create_task(self.check_offline_servers())
            
            # 添加回调以捕获启动时的潜在异常
            def _handle_start_exception(task):
                try:
                    task.result()
                except asyncio.CancelledError:
                    pass
                except Exception as ex:
                    logger.error(f"初始检查任务执行异常: {ex}")

            self._initial_task.add_done_callback(_handle_start_exception)

        except Exception as e:
            logger.error(f"启动离线服务器检查任务失败: {e}")
            self.is_running = False
            # 启动失败时确保清理资源
            await self.stop()
            raise

    async def stop(self):
        """停止定时任务并释放资源"""
        if not self.is_running:
            return

        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            
            # [资源清理] 取消正在运行的初始任务
            if self._initial_task and not self._initial_task.done():
                self._initial_task.cancel()
                try:
                    await self._initial_task
                except asyncio.CancelledError:
                    pass
            
            # [资源清理] 关闭私有线程池
            if self._executor:
                self._executor.shutdown(wait=False)
                
            logger.info("离线服务器检查服务已停止，线程池已释放")
        except Exception as e:
            logger.error(f"停止离线服务器检查任务失败: {e}")
            self.is_running = False

    async def check_offline_servers(self):
        """检查所有离线服务器的在线状态"""
        if self._is_checking:
            logger.warning("上一轮离线服务器检查任务尚未完成，跳过本次执行")
            return

        try:
            self._is_checking = True
            start_time = datetime.now()

            # 1. 获取所有离线服务器列表
            offline_servers = []
            async with AsyncSessionLocal() as session:
                stmt = select(Server).where(Server.status == ServerStatus.OFFLINE)
                result = await session.execute(stmt)
                offline_servers = result.scalars().all()

            if not offline_servers:
                logger.info("当前没有离线服务器，跳过检查")
                return

            logger.info(f"开始检查 {len(offline_servers)} 台离线服务器 (并发: {self._max_workers})")

            # 2. 创建异步队列
            server_queue = asyncio.Queue()
            for server in offline_servers:
                await server_queue.put(server)

            # 3. 创建消费者任务
            tasks = []
            for i in range(self._max_workers):
                task = asyncio.create_task(self._worker(server_queue, i))
                tasks.append(task)

            # 4. 等待所有消费者完成
            await asyncio.gather(*tasks, return_exceptions=True)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"离线服务器检查完成: 耗时 {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"定时检查离线服务器状态全局异常: {e}")
        finally:
            self._is_checking = False

    async def _worker(self, server_queue: asyncio.Queue, worker_id: int):
        """工作者协程"""
        while not server_queue.empty():
            try:
                server = server_queue.get_nowait()
                
                # 执行检查
                is_online = await self._check_server_connectivity(server)

                if is_online:
                    await self._update_server_status(server.id, ServerStatus.ONLINE)
                    logger.info(f"✅ 服务器 {server.id} ({server.ipmi_ip}) 已恢复在线")
            
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Worker-{worker_id} 处理异常: {e}")

    async def _check_server_connectivity(self, server: Server) -> bool:
        """
        检查服务器连通性 (UDP Hybrid Probe)
        """
        async with self._connectivity_semaphore:
            loop = asyncio.get_running_loop()

            # 捕获局部变量以便传入闭包
            total_timeout = self._total_timeout
            target_ip = server.ipmi_ip
            target_port = int(server.ipmi_port)
            
            def _udp_ping_sync():
                """同步 Socket 操作，将在私有线程池中运行"""
                # 策略: 3次重试，每次尝试占用总时间的 1/3
                max_retries = 3
                per_try_timeout = total_timeout / max_retries
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(per_try_timeout)
                
                try:
                    for attempt in range(max_retries):
                        try:
                            # --- 混合发包策略 ---
                            # 1. 发送 IPMI v2.0 包 (覆盖 95% 现代设备)
                            sock.sendto(PAYLOAD_V2, (target_ip, target_port))
                            
                            # 2. 紧接着发送 IPMI v1.5 包 (兼容老设备)
                            # UDP 发送几乎不耗时，同时发两个包可确保最大兼容性
                            sock.sendto(PAYLOAD_V1_5, (target_ip, target_port))
                            
                            # 3. 接收响应
                            # 只要收到任何数据，就说明端口开放且有 BMC 响应
                            data, _ = sock.recvfrom(1024)
                            
                            if len(data) > 0:
                                return True
                                
                        except (socket.timeout, OSError):
                            # 本次尝试超时或失败，继续下一次尝试
                            continue
                            
                    # 3次尝试均无响应
                    return False
                except Exception:
                    return False
                finally:
                    sock.close()

            try:
                # 关键：使用 run_in_executor 将阻塞 I/O 放入私有线程池
                return await loop.run_in_executor(self._executor, _udp_ping_sync)
            except Exception as e:
                logger.error(f"Executor check error {target_ip}: {e}")
                return False

    async def _update_server_status(self, server_id: int, status: ServerStatus):
        """更新服务器状态"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = update(Server).where(Server.id == server_id).values(status=status)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            logger.error(f"更新服务器 {server_id} 状态失败: {e}")

    def get_status(self) -> dict:
        """获取服务内部状态监控"""
        try:
            check_job = self.scheduler.get_job(self._check_job_id)
            return {
                "running": self.is_running,
                "concurrency": self._max_workers,
                "timeout_setting": self._total_timeout,
                "next_run": check_job.next_run_time.isoformat() if check_job and check_job.next_run_time else None
            }
        except Exception as e:
            return {"error": str(e)}