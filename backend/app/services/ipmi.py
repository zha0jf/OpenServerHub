import asyncio
import json
import logging
import multiprocessing
import queue
import time
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor  # 添加导入

import httpx
import redfish
from pyghmi.ipmi import command
from pyghmi.exceptions import IpmiException

from app.core.config import settings
from app.core.exceptions import IPMIError

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# 顶层工作函数 (Top-level Worker Functions)
# 这些函数在独立的子进程中运行，每次都是全新的环境
# 不需要 try...finally 清理，进程销毁时会自动回收资源
# -------------------------------------------------------------------------

def _mp_create_connection(ip, username, password, port):
    """辅助函数：创建连接"""
    return command.Command(
        bmc=ip,
        userid=username,
        password=password,
        port=port,
        keepalive=False,
        interface="lanplus",
        privlevel=4
    )

def _mp_get_power(ip, username, password, port):
    """进程内执行：获取电源状态"""
    try:
        conn = _mp_create_connection(ip, username, password, port)
        res = conn.get_power()
        return {"status": "success", "data": res.get('powerstate', 'unknown')}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _mp_set_power(ip, username, password, port, action):
    """进程内执行：设置电源"""
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
    """进程内执行：获取用户列表"""
    try:
        conn = _mp_create_connection(ip, username, password, port)
        users = conn.get_users()
        return {"status": "success", "data": users}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _mp_manage_user(ip, admin_user, admin_pass, port, operation, **kwargs):
    """进程内执行：用户管理通用函数"""
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
    """进程内执行：获取系统详细信息 (FRU + LAN)"""
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
            
            # 如果没找到，尝试取第一个
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
            # 内部辅助函数：简单修复编码
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
                if bmc_conf:
                    bmc_version = bmc_conf.get('firmware_version', 'Unknown')
            except: pass

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
    """进程内执行：获取并处理所有传感器数据"""
    try:
        conn = _mp_create_connection(ip, username, password, port)
        
        sensor_data = {"temperature": [], "voltage": [], "fan_speed": [], "other": []}
        unique_sensors = set()
        
        # 遍历传感器生成器
        for sensor in conn.get_sensor_data():
            if sensor.name in unique_sensors:
                continue
            unique_sensors.add(sensor.name)

            try:
                # 触发 value 读取
                val = sensor.value 
                
                # 获取属性
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
                if getattr(sensor, 'unavailable', False):
                    continue

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


# -------------------------------------------------------------------------
# 进程管理辅助函数
# -------------------------------------------------------------------------

def _run_task_in_fresh_process_safe(target_func, args, timeout):
    """
    改进版：
    1. 接收超时参数，避免硬编码 60s 导致线程阻塞。
    2. 确保在超时发生时，子进程被 kill。
    """
    def _worker_wrapper(q, func, func_args):
        try:
            result = func(*func_args)
            q.put({"status": "ok", "payload": result})
        except Exception as e:
            q.put({"status": "fail", "error": str(e)})

    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_worker_wrapper, args=(q, target_func, args))
    
    try:
        p.start()
        # 使用传入的 timeout，而不是硬编码
        p.join(timeout=timeout)
        
        if p.is_alive():
            p.terminate() # 尝试温和终止
            time.sleep(0.1)
            if p.is_alive():
                p.kill() # 强制杀死
            p.join() # 回收资源
            return {"status": "error", "error": f"IPMI子进程执行超时({timeout}s)"}
        
        if not q.empty():
            wrapper_res = q.get_nowait()
            if wrapper_res["status"] == "ok":
                return wrapper_res["payload"]
            else:
                return {"status": "error", "error": wrapper_res["error"]}
        else:
            # 进程退出了但队列为空（通常是 Crash）
            return {"status": "error", "error": "IPMI子进程异常退出且无返回数据"}
            
    except Exception as e:
        if p.is_alive():
            p.kill()
        return {"status": "error", "error": f"进程管理异常: {str(e)}"}
    finally:
        q.close()


# -------------------------------------------------------------------------
# 主服务类
# -------------------------------------------------------------------------

class IPMIService:
    """IPMI服务"""
    
    def __init__(self):
        # 1. 限制并发数：防止开启过多子进程导致死机
        # 建议根据机器配置调整，例如 CPU 核数 * 2
        self._semaphore = asyncio.Semaphore(settings.IPMI_CONCURRENT_LIMIT if hasattr(settings, 'IPMI_CONCURRENT_LIMIT') else 20) 
        
        # 2. 独立的线程池：防止阻塞任务耗尽全局线程池影响其他业务
        self._executor = ThreadPoolExecutor(max_workers=settings.IPMI_THREAD_POOL_SIZE if hasattr(settings, 'IPMI_THREAD_POOL_SIZE') else 20)
    
    def __del__(self):
        """析构函数，确保资源被正确释放"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
    
    def close(self):
        """关闭IPMI服务，释放资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)

    def _ensure_port_is_int(self, port):
        """确保端口是整数类型"""
        try:
            return int(port)
        except (ValueError, TypeError):
            raise IPMIError(f"端口参数无效: {port}")

    async def _run_in_process(self, func, *args, timeout=None):
        if timeout is None:
            timeout = settings.IPMI_TIMEOUT

        async with self._semaphore:  # 获取信号量
            loop = asyncio.get_running_loop()
            
            # 将超时逻辑传递给内部，确保子进程能被正确清理
            # 注意：这里我们传递 timeout + 2 秒给 wait_for，
            # 这里的 timeout 参数主要传给 _wrapper 内部去控制 join
            try:
                # 定义一个同步的阻塞函数，用来管理子进程
                def _blocking_process_runner():
                    return _run_task_in_fresh_process_safe(func, args, timeout)
                
                # 使用自定义线程池
                return await asyncio.wait_for(
                    loop.run_in_executor(
                        self._executor, 
                        _blocking_process_runner
                    ),
                    timeout=timeout + 5 # 给线程一点缓冲时间来清理进程
                )
            except asyncio.TimeoutError:
                raise IPMIError(f"IPMI操作超时({timeout}秒) - 任务强制取消")
            except Exception as e:
                if isinstance(e, IPMIError): 
                    raise
                raise IPMIError(f"IPMI操作异常: {str(e)}")

    async def get_power_state(self, ip: str, username: str, password: str, port: int = 623) -> str:
        """获取电源状态"""
        port = self._ensure_port_is_int(port)
        result = await self._run_in_process(_mp_get_power, ip, username, password, port)
        return result

    async def power_control(self, ip: str, username: str, password: str, action: str, port: int = 623) -> Dict[str, Any]:
        """电源控制"""
        port = self._ensure_port_is_int(port)
        result = await self._run_in_process(_mp_set_power, ip, username, password, port, action)
        return {"action": action, "result": "success", "message": f"电源{action}操作成功", "data": result}

    async def get_system_info(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """获取系统信息"""
        port = self._ensure_port_is_int(port)
        result = await self._run_in_process(_mp_get_system_info, ip, username, password, port, ip)
        return result

    async def get_sensor_data(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """获取传感器数据"""
        port = self._ensure_port_is_int(port)
        result = await self._run_in_process(_mp_get_sensor_data, ip, username, password, port)
        return result

    async def get_users(self, ip: str, username: str, password: str, port: int = 623) -> List[Dict[str, Any]]:
        """获取BMC用户列表"""
        port = self._ensure_port_is_int(port)
        result = await self._run_in_process(_mp_get_users, ip, username, password, port)
        return result

    async def create_user(self, ip: str, admin_username: str, admin_password: str, 
                         new_userid: int, new_username: str, new_password: str, 
                         priv_level: str = 'user', port: int = 623) -> bool:
        """创建BMC用户"""
        port = self._ensure_port_is_int(port)
        kwargs = {
            'uid': new_userid,
            'name': new_username,
            'password': new_password,
            'privilege_level': priv_level
        }
        result = await self._run_in_process(_mp_manage_user, ip, admin_username, admin_password, port, 'create', **kwargs)
        return True

    async def set_user_priv(self, ip: str, admin_username: str, admin_password: str,
                           userid: int, priv_level: str, port: int = 623) -> bool:
        """设置用户权限级别"""
        port = self._ensure_port_is_int(port)
        kwargs = {
            'uid': userid,
            'privilege_level': priv_level
        }
        result = await self._run_in_process(_mp_manage_user, ip, admin_username, admin_password, port, 'set_priv', **kwargs)
        return True

    async def set_user_password(self, ip: str, admin_username: str, admin_password: str,
                               userid: int, new_password: str, port: int = 623) -> bool:
        """设置用户密码"""
        port = self._ensure_port_is_int(port)
        kwargs = {
            'uid': userid,
            'password': new_password
        }
        result = await self._run_in_process(_mp_manage_user, ip, admin_username, admin_password, port, 'set_password', **kwargs)
        return True

    async def test_connection(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """测试IPMI连接"""
        port = self._ensure_port_is_int(port)
        try:
            result = await self.get_power_state(ip, username, password, port)
            return {
                "status": "success",
                "message": "IPMI连接测试成功",
                "power_state": result
            }
        except Exception as e:
            return {"status": "error", "message": f"IPMI连接失败: {str(e)}"}
    
    async def check_redfish_support(self, bmc_ip: str, timeout: int = 10) -> Dict[str, Any]:
        """
        检查服务器BMC是否支持Redfish功能
        
        Args:
            bmc_ip: BMC的IP地址
            timeout: 请求超时时间（秒），默认10秒
            
        Returns:
            Dict[str, Any]: 包含Redfish支持状态和相关信息的字典
                - supported: bool, 是否支持Redfish
                - version: str, Redfish版本（如果支持）
                - service_root: Dict, 服务根信息（如果支持）
                - error: str, 错误信息（如果不支持或发生错误）
                - check_success: bool, 检查是否成功执行（用于区分明确结果和检查失败）
        """
        import json
        import httpx
        start_time = time.time()
        try:
            logger.debug(f"[Redfish检查] 开始检查Redfish支持: {bmc_ip}")
            
            # 构建Redfish服务根URL
            redfish_url = f"https://{bmc_ip}/redfish/v1/"
            
            # 创建httpx异步客户端
            async with httpx.AsyncClient(
                verify=False,  # 忽略SSL证书验证（类似于curl -k参数）
                timeout=timeout
            ) as client:
                # 发送GET请求到Redfish服务根端点
                response = await client.get(redfish_url)
                
                execution_time = time.time() - start_time
                logger.debug(f"[Redfish检查] 请求完成: {bmc_ip}, 状态码: {response.status_code}, 耗时: {execution_time:.3f}秒")
                
                # 检查响应状态码
                if response.status_code == 200:
                    try:
                        # 解析JSON响应
                        service_root = response.json()
                        
                        # 提取Redfish版本信息
                        redfish_version = service_root.get("RedfishVersion", "Unknown")
                        
                        logger.info(f"[Redfish检查] BMC支持Redfish: {bmc_ip}, 版本: {redfish_version}")
                        
                        return {
                            "supported": True,
                            "version": redfish_version,
                            "service_root": service_root,
                            "error": None,
                            "check_success": True  # 明确的成功结果
                        }
                    except json.JSONDecodeError as e:
                        logger.warning(f"[Redfish检查] JSON解析失败: {bmc_ip}, 错误: {e}")
                        return {
                            "supported": False,
                            "version": None,
                            "service_root": None,
                            "error": f"JSON解析失败: {str(e)}",
                            "check_success": True  # 明确的失败结果（BMC返回了非JSON响应）
                        }
                else:
                    logger.info(f"[Redfish检查] BMC不支持Redfish或访问被拒绝: {bmc_ip}, 状态码: {response.status_code}")
                    return {
                        "supported": False,
                        "version": None,
                        "service_root": None,
                        "error": f"HTTP状态码: {response.status_code}",
                        "check_success": True  # 明确的失败结果（BMC返回了明确的错误码）
                    }
                    
        except httpx.TimeoutException:
            execution_time = time.time() - start_time
            logger.error(f"[Redfish检查] 请求超时: {bmc_ip}, 超时时间: {timeout}秒, 耗时: {execution_time:.3f}秒")
            return {
                "supported": False,
                "version": None,
                "service_root": None,
                "error": f"请求超时 ({timeout}秒)",
                "check_success": False  # 检查失败（网络问题）
            }
        except httpx.RequestError as e:
            execution_time = time.time() - start_time
            logger.error(f"[Redfish检查] 请求错误: {bmc_ip}, 错误: {e}, 耗时: {execution_time:.3f}秒")
            return {
                "supported": False,
                "version": None,
                "service_root": None,
                "error": f"请求错误: {str(e)}",
                "check_success": False  # 检查失败（网络问题）
            }
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[Redfish检查] 未知错误: {bmc_ip}, 错误: {e}, 耗时: {execution_time:.3f}秒")
            return {
                "supported": False,
                "version": None,
                "service_root": None,
                "error": f"未知错误: {str(e)}",
                "check_success": False  # 检查失败（其他异常）
            }
    
    async def get_redfish_led_status(self, bmc_ip: str, username: str, password: str, timeout: int = 10) -> Dict[str, Any]:
        """
        获取服务器LED状态（通过Redfish接口）
        
        Args:
            bmc_ip: BMC的IP地址
            username: Redfish用户名
            password: Redfish密码
            timeout: 请求超时时间（秒），默认10秒
            
        Returns:
            Dict[str, Any]: 包含LED状态信息的字典
                - supported: bool, 是否支持LED控制
                - led_state: str, LED状态（"On", "Off" 或 "Unknown"）
                - error: str, 错误信息（如果发生错误）
        """
        import redfish
        loop = asyncio.get_running_loop()
        
        def _get_led_status_sync():
            """同步函数，在线程池中执行Redfish操作"""
            try:
                # 创建Redfish客户端
                redfish_client = redfish.redfish_client(
                    base_url=f"https://{bmc_ip}",
                    username=username,
                    password=password,
                    default_prefix='/redfish/v1'
                )
                
                # 登录
                redfish_client.login(auth="session")
                
                # 获取系统信息
                systems_response = redfish_client.get("/redfish/v1/Systems")
                systems_data = systems_response.dict
                
                # 获取第一个系统
                if systems_data.get("Members"):
                    system_url = systems_data["Members"][0]["@odata.id"]
                    system_response = redfish_client.get(system_url)
                    system_data = system_response.dict
                    
                    # 获取LED状态
                    indicator_led = system_data.get("IndicatorLED", "Unknown")
                    
                    # 登出
                    redfish_client.logout()
                    
                    return {
                        "supported": True,
                        "led_state": indicator_led,
                        "error": None
                    }
                else:
                    # 登出
                    redfish_client.logout()
                    
                    return {
                        "supported": False,
                        "led_state": "Unknown",
                        "error": "未找到系统信息"
                    }
                    
            except Exception as e:
                logger.error(f"[Redfish LED状态] 获取LED状态失败: {bmc_ip}, 错误: {e}")
                return {
                    "supported": False,
                    "led_state": "Unknown",
                    "error": str(e)
                }
        
        try:
            logger.debug(f"[Redfish LED状态] 开始获取LED状态: {bmc_ip}")
            
            # 在线程池中执行同步的Redfish操作
            result = await loop.run_in_executor(None, _get_led_status_sync)
            
            logger.info(f"[Redfish LED状态] 获取LED状态完成: {bmc_ip}, 状态: {result.get('led_state')}")
            return result
            
        except Exception as e:
            logger.error(f"[Redfish LED状态] 未知错误: {bmc_ip}, 错误: {e}")
            return {
                "supported": False,
                "led_state": "Unknown",
                "error": f"未知错误: {str(e)}"
            }
    
    async def set_redfish_led_state(self, bmc_ip: str, username: str, password: str, led_state: str, timeout: int = 10) -> Dict[str, Any]:
        """
        设置服务器LED状态（通过Redfish接口）
        
        Args:
            bmc_ip: BMC的IP地址
            username: Redfish用户名
            password: Redfish密码
            led_state: LED状态（"On" 或 "Off"）
            timeout: 请求超时时间（秒），默认10秒
            
        Returns:
            Dict[str, Any]: 包含操作结果的字典
                - success: bool, 操作是否成功
                - message: str, 操作结果信息
                - error: str, 错误信息（如果发生错误）
        """
        import redfish
        # 定义不同厂商可能使用的LED状态命令，按优先级排序
        LED_STATE_COMMANDS = {
            "On": ["On", "Lit"],
            "Off": ["Off"],
            "Unknown": ["Unknown"]
        }

        loop = asyncio.get_running_loop()
        
        def _set_led_state_sync(led_command):
            """同步函数，在线程池中执行Redfish操作"""
            try:
                # 创建Redfish客户端
                redfish_client = redfish.redfish_client(
                    base_url=f"https://{bmc_ip}",
                    username=username,
                    password=password,
                    default_prefix='/redfish/v1'
                )
                
                # 登录
                redfish_client.login(auth="session")
                
                # 获取系统信息
                systems_response = redfish_client.get("/redfish/v1/Systems")
                systems_data = systems_response.dict
                
                # 获取第一个系统
                if systems_data.get("Members"):
                    system_url = systems_data["Members"][0]["@odata.id"]
                    
                    # 构建PATCH请求数据
                    patch_data = {
                        "IndicatorLED": led_command
                    }
                    
                    # 发送PATCH请求设置LED状态
                    response = redfish_client.patch(system_url, body=patch_data)
                    
                    # 登出
                    redfish_client.logout()
                    
                    return {
                        "success": response.status in [200, 204],
                        "status_code": response.status,
                        "error": None if response.status in [200, 204] else f"状态码: {response.status}"
                    }
                else:
                    # 登出
                    redfish_client.logout()
                    
                    return {
                        "success": False,
                        "status_code": None,
                        "error": "未找到系统信息"
                    }
                    
            except Exception as e:
                logger.error(f"[Redfish LED控制] 设置LED状态失败: {bmc_ip}, 错误: {e}")
                return {
                    "success": False,
                    "status_code": None,
                    "error": str(e)
                }
        
        try:
            logger.debug(f"[Redfish LED控制] 开始设置LED状态: {bmc_ip}, 状态: {led_state}")
            
            # 验证LED状态参数
            if led_state not in LED_STATE_COMMANDS:
                logger.warning(f"[Redfish LED控制] 无效的LED状态: {led_state}")
                return {
                    "success": False,
                    "message": "无效的LED状态",
                    "error": f"LED状态必须是 'On' 或 'Off'，当前值: {led_state}"
                }
            
            # 按顺序尝试不同的LED状态命令
            commands_to_try = LED_STATE_COMMANDS.get(led_state, [led_state])
            last_error = None
            
            for cmd in commands_to_try:
                logger.debug(f"[Redfish LED控制] 尝试使用命令 '{cmd}': {bmc_ip}")
                
                # 在线程池中执行同步的Redfish操作
                result = await loop.run_in_executor(None, _set_led_state_sync, cmd)
                
                # 如果成功（200或204），直接返回成功结果
                if result.get("success"):
                    logger.info(f"[Redfish LED控制] 设置LED状态成功: {bmc_ip}, 状态: {led_state} (使用命令: {cmd})")
                    return {
                        "success": True,
                        "message": f"LED状态已设置为 {led_state}",
                        "error": None
                    }
                
                # 记录错误信息，继续尝试下一个命令
                last_error = result.get("error")
                logger.debug(f"[Redfish LED控制] 使用命令 '{cmd}' 失败，错误: {last_error}")
            
            # 如果所有命令都失败了，返回最后一个错误
            logger.warning(f"[Redfish LED控制] 设置LED状态失败: {bmc_ip}, 最后错误: {last_error}")
            return {
                "success": False,
                "message": "设置LED状态失败",
                "error": last_error
            }
            
        except Exception as e:
            logger.error(f"[Redfish LED控制] 未知错误: {bmc_ip}, 错误: {e}")
            return {
                "success": False,
                "message": "操作失败",
                "error": f"未知错误: {str(e)}"
            }
    
    async def ensure_openshub_user(self, ip: str, admin_username: str, admin_password: str, port: int = 623) -> bool:
        """确保openshub监控用户存在且配置正确，强制更新密码为新密码"""
        try:
            start_time = time.time()
            logger.debug(f"[确保用户] 开始确保openshub用户存在: {ip}:{port}")
            # 1. 连接到BMC
            # 2. 获取用户列表
            users = await self.get_users(ip, admin_username, admin_password, port)
            
            openshub_user = None
            for user in users:
                # 确保user是字典类型再访问
                if isinstance(user, dict) and user.get('name', '').lower() == 'openshub':
                    openshub_user = user
                    break
            
            # 3. 如果用户不存在，则创建
            if not openshub_user:
                # 查找可用的用户ID（通常ID 10是安全的选择）
                new_userid = 10
                # 确保used_ids中的元素都是整数
                used_ids = []
                for user in users:
                    if isinstance(user, dict) and user.get('id') is not None:
                        try:
                            user_id = user.get('id')
                            if user_id is not None:
                                used_ids.append(int(user_id))
                        except (ValueError, TypeError):
                            pass
                
                while new_userid in used_ids and new_userid < 15:
                    new_userid += 1
                
                if new_userid >= 15:
                    logger.error(f"无法为服务器 {ip} 分配用户ID，用户槽位已满")
                    return False
                
                await self.create_user(
                    ip=ip,
                    admin_username=admin_username,
                    admin_password=admin_password,
                    new_userid=new_userid,
                    new_username='openshub',
                    new_password='0penS@hub',
                    priv_level='user',
                    port=port
                )
                logger.info(f"为服务器 {ip} 创建了 openshub 用户")
            else:
                # 4. 如果用户存在，更新密码和权限
                # 获取用户ID并确保不是None
                user_id = openshub_user.get('id')
                if user_id is not None:
                    try:
                        # 强制更新密码为新密码
                        await self.set_user_password(
                            ip=ip,
                            admin_username=admin_username,
                            admin_password=admin_password,
                            userid=int(user_id),
                            new_password='0penS@hub',
                            port=port
                        )
                        logger.info(f"更新了服务器 {ip} 上 openshub 用户的密码为新密码")
                    except Exception as e:
                        logger.warning(f"更新openshub用户密码失败 {ip}: {e}")
                    
                    # 更新权限
                    if openshub_user.get('priv_level', '').lower() != 'user':
                        await self.set_user_priv(
                            ip=ip,
                            admin_username=admin_username,
                            admin_password=admin_password,
                            userid=int(user_id),
                            priv_level='user',
                            port=port
                        )
                        logger.info(f"更新了服务器 {ip} 上 openshub 用户的权限")
            
            execution_time = time.time() - start_time
            logger.debug(f"[确保用户] 确保openshub用户存在完成: {ip}:{port}, 耗时: {execution_time:.3f}秒")
            return True
        except Exception as e:
            logger.error(f"确保openshub用户失败 {ip}: {e}")
            logger.exception(e)
            return False