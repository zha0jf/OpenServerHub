import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, List
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import httpx
import redfish
from pyghmi.ipmi import command
from pyghmi.exceptions import IpmiException

from app.core.config import settings
from app.core.exceptions import IPMIError
# 导入时间装饰器
from app.core.timing_decorator import timing_debug

logger = logging.getLogger(__name__)

# =================================================================================
# 第一部分：多进程工作函数 (Top-level Functions)
# 这些函数必须定义在类外部，以便 Python 的 multiprocessing 可以序列化 (pickle) 它们。
# 它们运行在独立的子进程中，拥有独立的 GIL，不会阻塞主程序。
# =================================================================================

def _mp_create_connection(ip, username, password, port):
    """辅助函数：创建连接对象"""
    return command.Command(
        bmc=ip,
        userid=username,
        password=password,
        port=port,
        keepalive=False,  # 进程池模式下，每次任务是一次性的，不保持连接
        interface=settings.IPMI_INTERFACE_TYPE,
        privlevel=settings.IPMI_PRIVILEGE_LEVEL
    )

def _mp_get_power(ip, username, password, port):
    """[子进程] 获取电源状态"""
    try:
        conn = _mp_create_connection(ip, username, password, port)
        res = conn.get_power()
        # pyghmi 返回格式通常是 {'powerstate': 'on'}
        return {"status": "success", "data": res.get('powerstate', 'unknown')}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _mp_set_power(ip, username, password, port, action):
    """[子进程] 设置电源"""
    power_actions = {'on': 'on', 'off': 'off', 'restart': 'reset', 'force_off': 'off', 'force_restart': 'cycle'}
    try:
        if action not in power_actions:
            return {"status": "error", "error": f"不支持的电源操作: {action}"}
        
        conn = _mp_create_connection(ip, username, password, port)
        res = conn.set_power(power_actions[action])
        return {"status": "success", "data": res}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _mp_get_users(ip, username, password, port):
    """[子进程] 获取用户列表"""
    try:
        conn = _mp_create_connection(ip, username, password, port)
        users = conn.get_users()
        return {"status": "success", "data": users}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _mp_manage_user(ip, admin_user, admin_pass, port, operation, **kwargs):
    """[子进程] 用户管理通用函数"""
    try:
        conn = _mp_create_connection(ip, admin_user, admin_pass, port)
        
        if operation == 'create':
            conn.create_user(
                uid=kwargs['uid'], name=kwargs['name'], 
                password=kwargs['password'], privilege_level=kwargs['privilege_level']
            )
        elif operation == 'set_priv':
            conn.set_user_priv(uid=kwargs['uid'], privilege_level=kwargs['privilege_level'])
        elif operation == 'set_password':
            conn.set_user_password(uid=kwargs['uid'], mode='set_password', password=kwargs['password'])
            
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _mp_get_system_info(ip, username, password, port, initial_ip):
    """[子进程] 获取系统详细信息 (FRU + LAN)"""
    # 完整保留原有逻辑，确保解析结果一致
    results = {}
    try:
        conn = _mp_create_connection(ip, username, password, port)
        
        # 1. 获取系统清单
        system_info = None
        try:
            inventory_generator = conn.get_inventory()
            for name, info in inventory_generator:
                if isinstance(info, dict):
                    if (info.get('Manufacturer') or info.get('Board manufacturer') or 
                        info.get('Product name') or info.get('Board product name')):
                        system_info = info
                        break
            
            if not system_info:
                inventory_generator = conn.get_inventory()
                try:
                    _, system_info = next(inventory_generator)
                except StopIteration:
                    pass
        except Exception:
            pass

        # 解析 FRU 信息
        manufacturer = 'Unknown'
        product = 'Unknown'
        serial = 'Unknown'
        bmc_version = 'Unknown'

        if system_info and isinstance(system_info, dict):
            def fix_encoding(text):
                if not text or text == 'Unknown': return text
                try:
                    if 'å' in text or '¤' in text:
                        return text.encode('latin-1').decode('utf-8')
                except: pass
                try: return text.encode('latin-1').decode('gbk')
                except: pass
                return text

            manufacturer = (system_info.get('Manufacturer') or system_info.get('Board manufacturer') or 
                            system_info.get('Mfg') or system_info.get('Vendor') or 'Unknown')
            
            if manufacturer == 'Unknown':
                prod = (system_info.get('Product name') or '').lower()
                if 'dell' in prod: manufacturer = 'Dell'
                elif 'hp' in prod: manufacturer = 'HPE'
                elif 'lenovo' in prod: manufacturer = 'Lenovo'
                elif 'huawei' in prod: manufacturer = 'Huawei'
                elif 'inspur' in prod: manufacturer = 'Inspur'

            product = (system_info.get('Product name') or system_info.get('Board product name') or 
                       system_info.get('Product') or system_info.get('Model') or 'Unknown')
            
            serial = (system_info.get('Serial Number') or system_info.get('Board serial number') or 
                      system_info.get('Chassis serial number') or system_info.get('Serial') or 'Unknown')
            
            bmc_version = (system_info.get('firmware_version') or system_info.get('Firmware Version') or 
                           system_info.get('Version') or 'Unknown')

            manufacturer = fix_encoding(manufacturer)
            product = fix_encoding(product)

        # 2. 获取 LAN 配置
        bmc_ip = initial_ip
        bmc_mac = 'Unknown'
        try:
            lan_info = conn.get_net_configuration(channel=1)
            if lan_info:
                bmc_ip = lan_info.get('ipv4_address', initial_ip).split('/')[0]
                bmc_mac = lan_info.get('mac_address', 'Unknown')
        except Exception:
            pass
        
        # 尝试备用方法获取 BMC 版本
        if bmc_version == 'Unknown':
            try:
                bmc_conf = conn.get_bmc_configuration()
                if bmc_conf and isinstance(bmc_conf, dict):
                    bmc_version = bmc_conf.get('firmware_version', 'Unknown')
            except Exception:
                pass

        return {
            "status": "success",
            "data": {
                "manufacturer": manufacturer,
                "product": product,
                "serial": serial,
                "bmc_ip": bmc_ip,
                "bmc_mac": bmc_mac,
                "bmc_version": bmc_version
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _mp_get_sensor_data(ip, username, password, port):
    """[子进程] 获取传感器数据"""
    try:
        conn = _mp_create_connection(ip, username, password, port)
        sensor_data = {"temperature": [], "voltage": [], "fan_speed": [], "other": []}
        unique_sensors = set()
        
        for sensor in conn.get_sensor_data():
            if sensor.name in unique_sensors: continue
            unique_sensors.add(sensor.name)

            try:
                val = sensor.value 
                health = 'Unknown'
                if hasattr(sensor, '_reading') and sensor._reading:
                    health = getattr(sensor._reading, 'health', 'Unknown')
                
                info = {
                    "name": sensor.name,
                    "value": float(val) if val is not None else 0.0,
                    "unit": getattr(sensor, 'units', ''),
                    "status": health
                }
                
                s_type = str(getattr(sensor, 'type', '')).lower()
                if getattr(sensor, 'unavailable', False): continue

                if 'temp' in s_type or 'thermal' in s_type:
                    sensor_data["temperature"].append(info)
                elif 'voltage' in s_type or 'volt' in s_type:
                    sensor_data["voltage"].append(info)
                elif 'fan' in s_type or 'rpm' in s_type:
                    sensor_data["fan_speed"].append(info)
                else:
                    sensor_data["other"].append(info)
            except Exception:
                continue

        return {"status": "success", "data": sensor_data}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =================================================================================
# 第二部分：IPMI 服务类
# =================================================================================

class IPMIService:
    """IPMI服务"""
    
    _process_pool = None
    _thread_pool = None

    def __init__(self):
        # 1. 初始化进程池（单例模式，避免重复创建）
        # 用于 pyghmi 这种可能导致 GIL 锁死的操作
        if IPMIService._process_pool is None:
            max_procs = getattr(settings, 'IPMI_PROCESS_POOL_SIZE', 4)
            try:
                IPMIService._process_pool = ProcessPoolExecutor(
                    max_workers=max_procs, 
                    max_tasks_per_child=1  # 仅 Python 3.11+ 支持
                )
            except TypeError:
                # 旧版本 Python 不支持此参数，回退到默认
                IPMIService._process_pool = ProcessPoolExecutor(max_workers=max_procs)
            logger.info(f"IPMI ProcessPoolExecutor started with {max_procs} workers")
        
        # 2. 初始化线程池
        # 用于 Redfish 等 IO 密集型操作
        if IPMIService._thread_pool is None:
            max_threads = getattr(settings, 'IPMI_THREAD_POOL_SIZE', 20)
            IPMIService._thread_pool = ThreadPoolExecutor(max_workers=max_threads)
        
        # 3. 信号量控制并发请求数
        limit = getattr(settings, 'IPMI_CONCURRENT_LIMIT', 20)
        self._semaphore = asyncio.Semaphore(limit)

    def close(self):
        """关闭服务资源"""
        # 注意：通常在应用生命周期结束时才真正关闭池，或者这里留空让 OS 回收
        pass

    def _ensure_port_is_int(self, port):
        try:
            return int(port)
        except (ValueError, TypeError):
            raise IPMIError(f"端口参数无效: {port}")

    async def _run_in_process(self, func, *args, timeout=None):
        """
        核心调度函数：将任务提交给进程池，并带有严格的超时控制。
        """
        if timeout is None:
            timeout = getattr(settings, 'IPMI_TIMEOUT', 10)

        loop = asyncio.get_running_loop()
        
        async with self._semaphore:
            try:
                # 使用 wait_for 在主进程层面强制控制超时
                # 即便子进程卡死，主进程也会抛出 TimeoutError 并继续运行
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        IPMIService._process_pool, 
                        func, 
                        *args
                    ),
                    timeout=timeout
                )
                
                # 检查子进程返回的数据结构
                if isinstance(result, dict):
                    if result.get("status") == "success":
                        return result.get("data") # 成功返回数据
                    else:
                        # 业务逻辑错误（连接失败等）
                        error_msg = result.get("error", "未知错误")
                        raise IPMIError(error_msg)
                return result

            except asyncio.TimeoutError:
                logger.error(f"IPMI 任务超时 ({timeout}s) - 调用: {func.__name__}")
                raise IPMIError(f"IPMI操作超时({timeout}秒)")
            except IPMIError:
                raise
            except Exception as e:
                logger.error(f"IPMI 执行异常: {e}")
                raise IPMIError(f"执行异常: {str(e)}")

    async def _run_in_thread(self, func, *args):
        """在线程池中运行（适用于 Redfish/Requests 库）"""
        loop = asyncio.get_running_loop()
        async with self._semaphore:
            return await loop.run_in_executor(
                IPMIService._thread_pool,
                func,
                *args
            )

    # ---------------------------------------------------------------------
    # 公共 API 方法 (保持签名与原代码完全一致)
    # ---------------------------------------------------------------------

    @timing_debug
    async def get_power_state(self, ip: str, username: str, password: str, port: int = settings.IPMI_DEFAULT_PORT) -> str:
        """获取电源状态"""
        port = self._ensure_port_is_int(port)
        try:
            # 增加超时宽限，因为建立连接可能较慢
            return await self._run_in_process(_mp_get_power, ip, username, password, port, timeout=settings.IPMI_POWER_STATE_TIMEOUT)
        except IPMIError as e:
            # 原代码在这里可能抛出异常，或者返回 unknown。
            # 为了定时任务的健壮性，建议如果是超时或连接失败，记录日志并返回 "unknown"
            # 这样 Scheduler Service 里的 .lower() 就不会报错了 (如果是 unknown)
            logger.warning(f"获取电源状态失败 {ip}: {str(e)}")
            return "unknown"  # 返回字符串，防止 None.lower() 报错

    @timing_debug
    async def power_control(self, ip: str, username: str, password: str, action: str, port: int = settings.IPMI_DEFAULT_PORT) -> Dict[str, Any]:
        """电源控制"""
        port = self._ensure_port_is_int(port)
        # 操作类命令通常很快，但重启可能慢
        res = await self._run_in_process(_mp_set_power, ip, username, password, port, action, timeout=settings.IPMI_POWER_CONTROL_TIMEOUT)
        return {"action": action, "result": "success", "message": f"电源{action}操作成功", "data": res}

    @timing_debug
    async def get_system_info(self, ip: str, username: str, password: str, port: int = settings.IPMI_DEFAULT_PORT, timeout: int = None) -> Dict[str, Any]:
        """获取系统信息"""
        port = self._ensure_port_is_int(port)
        # 系统信息获取包含大量命令，需要较长时间
        return await self._run_in_process(_mp_get_system_info, ip, username, password, port, ip, timeout=timeout or settings.IPMI_SYSTEM_INFO_TIMEOUT)

    @timing_debug
    async def get_sensor_data(self, ip: str, username: str, password: str, port: int = settings.IPMI_DEFAULT_PORT) -> Dict[str, Any]:
        """获取传感器数据"""
        port = self._ensure_port_is_int(port)
        # 传感器遍历非常慢，给足时间
        return await self._run_in_process(_mp_get_sensor_data, ip, username, password, port, timeout=settings.IPMI_SENSOR_DATA_TIMEOUT)

    @timing_debug
    async def get_users(self, ip: str, username: str, password: str, port: int = settings.IPMI_DEFAULT_PORT) -> List[Dict[str, Any]]:
        """获取用户列表"""
        port = self._ensure_port_is_int(port)
        return await self._run_in_process(_mp_get_users, ip, username, password, port)

    async def create_user(self, ip: str, admin_username: str, admin_password: str, 
                         new_userid: int, new_username: str, new_password: str, 
                         priv_level: str = 'user', port: int = settings.IPMI_DEFAULT_PORT) -> bool:
        port = self._ensure_port_is_int(port)
        kwargs = {'uid': new_userid, 'name': new_username, 'password': new_password, 'privilege_level': priv_level}
        await self._run_in_process(_mp_manage_user, ip, admin_username, admin_password, port, 'create', **kwargs)
        return True

    async def set_user_priv(self, ip: str, admin_username: str, admin_password: str,
                           userid: int, priv_level: str, port: int = settings.IPMI_DEFAULT_PORT) -> bool:
        port = self._ensure_port_is_int(port)
        kwargs = {'uid': userid, 'privilege_level': priv_level}
        await self._run_in_process(_mp_manage_user, ip, admin_username, admin_password, port, 'set_priv', **kwargs)
        return True

    async def set_user_password(self, ip: str, admin_username: str, admin_password: str,
                               userid: int, new_password: str, port: int = settings.IPMI_DEFAULT_PORT) -> bool:
        port = self._ensure_port_is_int(port)
        kwargs = {'uid': userid, 'password': new_password}
        await self._run_in_process(_mp_manage_user, ip, admin_username, admin_password, port, 'set_password', **kwargs)
        return True

    @timing_debug
    async def test_connection(self, ip: str, username: str, password: str, port: int = settings.IPMI_DEFAULT_PORT) -> Dict[str, Any]:
        """测试连接"""
        try:
            state = await self.get_power_state(ip, username, password, port)
            if state and state != "unknown":
                return {"status": "success", "message": "IPMI连接测试成功", "power_state": state}
            else:
                return {"status": "error", "message": "无法获取电源状态"}
        except Exception as e:
            return {"status": "error", "message": f"IPMI连接失败: {str(e)}"}

    # ---------------------------------------------------------------------
    # Redfish 方法
    # ---------------------------------------------------------------------

    @timing_debug
    async def check_redfish_support(self, bmc_ip: str, timeout: int = settings.REDFISH_TIMEOUT) -> Dict[str, Any]:
        """检查 Redfish 支持 (使用原生异步 httpx)"""
        async with self._semaphore:
            start_time = time.time()
            try:
                # httpx.AsyncClient 原生支持异步，不需要放进线程池/进程池
                async with httpx.AsyncClient(verify=settings.REDFISH_VERIFY_SSL, timeout=timeout) as client:
                    response = await client.get(f"https://{bmc_ip}/redfish/v1/")
                    
                    if response.status_code == 200:
                        try:
                            service_root = response.json()
                            redfish_version = service_root.get("RedfishVersion", "Unknown")
                            logger.info(f"[Redfish] 支持: {bmc_ip}, Ver: {redfish_version}")
                            return {
                                "supported": True, "version": redfish_version, 
                                "service_root": service_root, "error": None, "check_success": True
                            }
                        except json.JSONDecodeError as e:
                            return {
                                "supported": False, "version": None, "service_root": None, 
                                "error": f"JSON Error: {e}", "check_success": True
                            }
                    else:
                        return {
                            "supported": False, "version": None, "service_root": None, 
                            "error": f"HTTP {response.status_code}", "check_success": True
                        }
            except Exception as e:
                logger.error(f"[Redfish] Error {bmc_ip}: {e}")
                return {
                    "supported": False, "version": None, "service_root": None, 
                    "error": str(e), "check_success": False
                }

    @timing_debug
    async def get_redfish_led_status(self, bmc_ip: str, username: str, password: str, timeout: int = settings.REDFISH_TIMEOUT) -> Dict[str, Any]:
        """获取 LED 状态 (同步库，跑在线程池)"""
        logger.debug(f"开始获取服务器 {bmc_ip} 的LED状态")
        def _sync_task():
            try:
                logger.debug(f"创建Redfish客户端连接 {bmc_ip}")
                redfish_client = redfish.redfish_client(
                    base_url=f"https://{bmc_ip}", username=username, password=password, 
                    default_prefix='/redfish/v1', timeout=timeout)
                logger.debug(f"登录到Redfish服务器 {bmc_ip}")
                redfish_client.login(auth="session")
                try:
                    logger.debug(f"获取系统信息 {bmc_ip}")
                    sys_resp = redfish_client.get("/redfish/v1/Systems")
                    if sys_resp.dict.get("Members"):
                        sys_url = sys_resp.dict["Members"][0]["@odata.id"]
                        logger.debug(f"获取LED状态 {bmc_ip}")
                        resp = redfish_client.get(sys_url)
                        result = {"supported": True, "led_state": resp.dict.get("IndicatorLED", "Unknown"), "error": None}
                        logger.debug(f"获取LED状态成功 {bmc_ip}: {result}")
                        return result
                    result = {"supported": False, "led_state": "Unknown", "error": "System not found"}
                    logger.debug(f"未找到系统信息 {bmc_ip}: {result}")
                    return result
                finally:
                    redfish_client.logout()
            except Exception as e:
                logger.debug(f"获取LED状态异常 {bmc_ip}: {str(e)}")
                return {"supported": False, "led_state": "Unknown", "error": str(e)}

        result = await self._run_in_thread(_sync_task)
        logger.debug(f"获取服务器 {bmc_ip} LED状态完成: {result}")
        return result

    @timing_debug
    async def set_redfish_led_state(self, bmc_ip: str, username: str, password: str, led_state: str, timeout: int = settings.REDFISH_TIMEOUT) -> Dict[str, Any]:
        """设置 LED 状态 (同步库，跑在线程池)"""
        logger.debug(f"开始设置服务器 {bmc_ip} 的LED状态为 {led_state}")
        def _sync_task(cmd):
            try:
                logger.debug(f"创建Redfish客户端连接 {bmc_ip} 设置LED状态 {cmd}")
                redfish_client = redfish.redfish_client(
                    base_url=f"https://{bmc_ip}", username=username, password=password, 
                    default_prefix='/redfish/v1', timeout=timeout)
                logger.debug(f"登录到Redfish服务器 {bmc_ip} 设置LED状态 {cmd}")
                redfish_client.login(auth="session")
                try:
                    logger.debug(f"获取系统信息 {bmc_ip}")
                    sys_resp = redfish_client.get("/redfish/v1/Systems")
                    if sys_resp.dict.get("Members"):
                        sys_url = sys_resp.dict["Members"][0]["@odata.id"]
                        logger.debug(f"设置LED状态 {bmc_ip} 为 {cmd}")
                        resp = redfish_client.patch(sys_url, body={"IndicatorLED": cmd})
                        success = resp.status in [200, 204]
                        result = {"success": success, "status_code": resp.status, "error": None if success else f"Status: {resp.status}"}
                        logger.debug(f"设置LED状态结果 {bmc_ip}: {result}")
                        return result
                    result = {"success": False, "status_code": None, "error": "System not found"}
                    logger.debug(f"未找到系统信息 {bmc_ip}: {result}")
                    return result
                finally:
                    redfish_client.logout()
            except Exception as e:
                logger.debug(f"设置LED状态异常 {bmc_ip}: {str(e)}")
                return {"success": False, "status_code": None, "error": str(e)}

        # 尝试不同的命令别名
        commands = {"On": ["On", "Lit"], "Off": ["Off"]}
        cmds_to_try = commands.get(led_state, [led_state])
        logger.debug(f"尝试设置LED状态 {bmc_ip} 为 {led_state}, 命令列表: {cmds_to_try}")
        
        last_error = None
        for cmd in cmds_to_try:
            logger.debug(f"尝试命令 {cmd} 设置LED状态 {bmc_ip}")
            res = await self._run_in_thread(_sync_task, cmd)
            logger.debug(f"命令 {cmd} 执行结果: {res}")
            if res.get("success"):
                result = {"success": True, "message": f"LED set to {led_state}", "error": None}
                logger.debug(f"设置LED状态成功 {bmc_ip}: {result}")
                return result
            last_error = res.get("error")
            
        result = {"success": False, "message": "Failed", "error": last_error}
        logger.debug(f"设置LED状态失败 {bmc_ip}: {result}")
        return result

    async def ensure_openshub_user(self, ip: str, admin_username: str, admin_password: str, port: int = settings.IPMI_DEFAULT_PORT) -> bool:
        """确保 openshub 用户存在 (逻辑保持不变，调用新版异步方法)"""
        try:
            # 复用 get_users (已是异步且进程隔离)
            users_res = await self.get_users(ip, admin_username, admin_password, port)
            
            # 注意：get_users 返回的是列表，不是字典结构(根据你的原始 _mp_get_users 实现)
            # 但为了保险，我们检查一下它是否是 dict (兼容 _run_in_process 的异常返回)
            users = users_res if isinstance(users_res, list) else []
            
            openshub_user = None
            for user in users:
                if isinstance(user, dict) and user.get('name', '').lower() == 'openshub':
                    openshub_user = user
                    break
            
            if not openshub_user:
                # 创建逻辑
                new_userid = 10
                used_ids = [int(u.get('id')) for u in users if isinstance(u, dict) and u.get('id') is not None]
                while new_userid in used_ids and new_userid < 15:
                    new_userid += 1
                
                if new_userid >= 15:
                    logger.error(f"无法分配用户ID: {ip}")
                    return False
                
                await self.create_user(ip, admin_username, admin_password, new_userid, 'openshub', '0penS@hub', 'user', port)
                logger.info(f"已创建 openshub 用户: {ip}")
            else:
                # 更新逻辑
                uid = int(openshub_user.get('id'))
                await self.set_user_password(ip, admin_username, admin_password, uid, '0penS@hub', port)
                
                if openshub_user.get('priv_level', '').lower() != 'user':
                    await self.set_user_priv(ip, admin_username, admin_password, uid, 'user', port)
            
            return True
        except Exception as e:
            logger.error(f"确保用户失败 {ip}: {e}")
            return False