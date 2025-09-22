import asyncio
import logging
import ipaddress
import functools  # 导入 functools
from typing import Dict, Any, Optional, Generator
from pyghmi.ipmi import command
from pyghmi.exceptions import IpmiException
from pyghmi.ipmi.sdr import SensorReading

from app.core.config import settings
from app.core.exceptions import IPMIError

logger = logging.getLogger(__name__)

class IPMIConnectionPool:
    """IPMI连接池管理"""
    
    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self.connections = {}
        self.semaphore = asyncio.Semaphore(max_connections)
    
    async def get_connection1(self, ip: str, username: str, password: str, port: int = 623):
        """获取IPMI连接（安全版，确保参数类型正确）"""
        # 确保参数类型
        try:
            ip = str(ip)
            port = int(port)
            username = str(username) if username is not None else ""
            password = str(password) if password is not None else ""
        except (ValueError, TypeError) as e:
            logger.error(f"IPMI连接参数类型无效: ip={ip}({type(ip)}), port={port}({type(port)}), "
                        f"user={username}({type(username)}), password={password}({type(password)})")
            raise IPMIError(f"IPMI连接参数类型错误: {e}")

        connection_key = f"{ip}:{port}:{username}"

        async with self.semaphore:
            try:
                logger.info(f"准备创建IPMI连接: bmc={repr(ip)}, port={port}, user={repr(username)}, password={repr(password)}")

                if connection_key not in self.connections:
                    conn = command.Command(
                        bmc=ip,
                        userid=username,
                        password=password,
                        port=port,
                        keepalive=True,
                        interface="lanplus",
                        privlevel=4
                    )
                    self.connections[connection_key] = conn

                return self.connections[connection_key]

            except TypeError as e:
                logger.error(f"TypeError创建IPMI连接失败: {e}")
                logger.error(f"参数: bmc={repr(ip)}, port={repr(port)}, user={repr(username)}, password={repr(password)}")
                raise IPMIError(f"IPMI连接失败（类型错误）: {e}")

            except Exception as e:
                # 处理pyghmi库内部的特定错误
                error_msg = str(e)
                if "'Session' object has no attribute 'errormsg'" in error_msg:
                    logger.error(f"创建IPMI连接失败: IPMI会话初始化失败，可能是网络连接问题或认证失败")
                    raise IPMIError(f"IPMI连接失败: 无法建立IPMI会话，请检查网络连接和认证信息")
                else:
                    logger.error(f"创建IPMI连接失败: {e}")
                    raise IPMIError(f"IPMI连接失败: {e}")
    async def get_connection(self, ip: str, username: str, password: str, port: int = 623, timeout: int = 5):
        """获取IPMI连接（安全版，带超时保护，避免在OpenBMC卡死）"""
        # 参数检查
        try:
            ip = str(ip)
            port = int(port)
            username = str(username) if username is not None else ""
            password = str(password) if password is not None else ""
        except (ValueError, TypeError) as e:
            logger.error(f"IPMI连接参数类型无效: ip={ip}, port={port}, user={username}, password={password}")
            raise IPMIError(f"IPMI连接参数类型错误: {e}")

        connection_key = f"{ip}:{port}:{username}"

        async with self.semaphore:
            if connection_key in self.connections:
                return self.connections[connection_key]

            loop = asyncio.get_running_loop()

            def _make_conn():
                return command.Command(
                    bmc=ip,
                    userid=username,
                    password=password,
                    port=port,
                    keepalive=True,
                    interface="lanplus",
                    privlevel=4
                )

            try:
                # 在子线程里跑，并设置超时
                conn = await asyncio.wait_for(loop.run_in_executor(None, _make_conn), timeout=timeout)
                self.connections[connection_key] = conn
                return conn
            except asyncio.TimeoutError:
                logger.error(f"创建IPMI连接超时: {ip}:{port}")
                raise IPMIError(f"IPMI连接超时: {ip}:{port}")
            except Exception as e:
                logger.error(f"创建IPMI连接失败: {e}")
                raise IPMIError(f"IPMI连接失败: {e}")

# 全局连接池实例
ipmi_pool = IPMIConnectionPool(settings.IPMI_CONNECTION_POOL_SIZE)

class IPMIService:
    """IPMI服务"""
    
    def __init__(self):
        self.pool = ipmi_pool
    
    async def _run_sync_ipmi(self, func, *args, **kwargs):
        """在线程池中运行同步的IPMI命令以避免阻塞事件循环"""
        loop = asyncio.get_running_loop()
        # 使用 functools.partial 封装函数和其参数
        partial_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, partial_func)

    def _ensure_port_is_int(self, port):
        """确保端口是整数类型"""
        try:
            if not isinstance(port, int):
                return int(port)
            return port
        except (ValueError, TypeError) as e:
            logger.error(f"端口参数无法转换为整数: {port}, 类型: {type(port)}")
            raise IPMIError(f"端口参数无效: {port}")
    
    async def get_power_state(self, ip: str, username: str, password: str, port: int = 623) -> str:
        """获取电源状态"""
        port = self._ensure_port_is_int(port)
        try:
            conn = await self.pool.get_connection(ip, username, password, port)
            result = await self._run_sync_ipmi(conn.get_power)
            return result.get('powerstate', 'unknown')
        except IpmiException as e:
            logger.error(f"获取电源状态失败 {ip}: {e}")
            raise IPMIError(f"获取电源状态失败: {str(e)}")
        except Exception as e:
            # 处理pyghmi库内部的特定错误
            error_msg = str(e)
            if "'Session' object has no attribute 'errormsg'" in error_msg:
                logger.error(f"IPMI操作异常 {ip}: IPMI会话初始化失败，可能是网络连接问题或认证失败")
                raise IPMIError(f"IPMI操作失败: 无法建立IPMI会话，请检查网络连接和认证信息")
            else:
                logger.error(f"IPMI操作异常 {ip}: {e}")
                raise IPMIError(f"IPMI操作失败: {str(e)}")
    
    async def power_control(self, ip: str, username: str, password: str, action: str, port: int = 623) -> Dict[str, Any]:
        """电源控制"""
        port = self._ensure_port_is_int(port)
        try:
            conn = await self.pool.get_connection(ip, username, password, port)
            
            power_actions = {'on': 'on', 'off': 'off', 'restart': 'reset', 'force_off': 'off'}
            if action not in power_actions:
                raise IPMIError(f"不支持的电源操作: {action}")
            
            await self._run_sync_ipmi(conn.set_power, power_actions[action])
            
            return {"action": action, "result": "success", "message": f"电源{action}操作成功"}
            
        except IpmiException as e:
            logger.error(f"电源控制失败 {ip} {action}: {e}")
            raise IPMIError(f"电源控制失败: {str(e)}")
        except Exception as e:
            # 处理pyghmi库内部的特定错误
            error_msg = str(e)
            if "'Session' object has no attribute 'errormsg'" in error_msg:
                logger.error(f"IPMI操作异常 {ip} {action}: IPMI会话初始化失败，可能是网络连接问题或认证失败")
                raise IPMIError(f"IPMI操作失败: 无法建立IPMI会话，请检查网络连接和认证信息")
            else:
                logger.error(f"IPMI操作异常 {ip} {action}: {e}")
                raise IPMIError(f"IPMI操作失败: {str(e)}")
    
    def _sync_get_all_info(self, conn: "command.Command", initial_ip: str) -> Dict[str, Any]:
        """
        [重写后] 同步辅助函数：获取系统清单和LAN配置，兼容当前版本 pyghmi。
        """
        results = {}

        # 1. 获取系统清单 (FRU, 固件版本等)
        try:
            # get_inventory() 是一个生成器，我们主要需要第一个 "System" 组件的信息
            inventory_generator = conn.get_inventory()
            system_name, system_info = next(inventory_generator)

            if system_name == "System" and system_info:
                # 根据实际返回的嵌套字典结构来提取信息
                board_info = system_info.get('Board', {})
                product_info = system_info.get('Product', {})

                results['manufacturer'] = board_info.get('Manufacturer', 'Unknown')
                results['product'] = product_info.get('Name', 'Unknown')
                results['serial'] = product_info.get('Serial Number', 'Unknown')
                results['bmc_version'] = system_info.get('Firmware Version', 'Unknown')

        except StopIteration:
            logger.info(f"获取系统清单失败: get_inventory() 未返回任何信息。")
        except Exception as e:
            logger.info(f"同步获取系统清单时发生错误: {e}")

        # 2. 获取LAN网络配置
        try:
            # 使用 get_net_configuration() 替代不存在的 get_lan_config()
            lan_info = conn.get_net_configuration(channel=1)  # 默认使用通道1
            if lan_info:
                # ipv4_address 可能带有 CIDR 后缀，需要去除
                bmc_ip = lan_info.get('ipv4_address', initial_ip).split('/')[0]
                results['bmc_ip'] = bmc_ip or initial_ip
                results['bmc_mac'] = lan_info.get('mac_address', 'Unknown')
            else:
                results['bmc_ip'] = initial_ip
                results['bmc_mac'] = 'Unknown'

        except Exception as e:
            logger.info(f"同步获取LAN配置失败: {e}")

        return results

    async def get_system_info(self, ip: str, username: str, password: str, port: int = 623, timeout: int = 30) -> Dict[str, Any]:
        """获取系统信息 (使用正确的 pyghmi.ipmi.command API)"""
        port = self._ensure_port_is_int(port)
        timeout = self._ensure_port_is_int(timeout)
        try:
            logger.info(f"开始获取系统信息: {ip}:{port} 用户:{username}")
            
            conn = await self.pool.get_connection(ip, username, password, port)
            
            # 在线程池中执行所有同步操作
            system_info = await asyncio.wait_for(
                self._run_sync_ipmi(self._sync_get_all_info, conn, ip),
                timeout=timeout
            )
            
            # 为未获取到的信息提供默认值
            final_info = {
                "manufacturer": system_info.get('manufacturer', 'Unknown'),
                "product": system_info.get('product', 'Unknown'),
                "serial": system_info.get('serial', 'Unknown'),
                "bmc_ip": system_info.get('bmc_ip', ip),
                "bmc_mac": system_info.get('bmc_mac', 'Unknown'),
                "bmc_version": system_info.get('bmc_version', 'Unknown'),
            }

            logger.info(f"系统信息获取成功: {ip}:{port} - {final_info}")
            return final_info
            
        except asyncio.TimeoutError:
            logger.warning(f"获取系统信息超时 {ip}:{port}")
            raise IPMIError("获取系统信息超时")
        except IpmiException as e:
            logger.error(f"获取系统信息失败 {ip}:{port}: {e}")
            raise IPMIError(f"获取系统信息失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}:{port}: {e}", exc_info=True)
            raise IPMIError(f"IPMI操作失败: {str(e)}")

    def _sync_fetch_and_parse_sensors(self, conn: command.Command) -> Dict[str, Any]:
        """同步函数：获取并解析所有传感器数据。此函数将在线程池中运行。"""
        sensors = {}
        try:
            sensors_generator = conn.get_sensor_data()
            for sensor_reading in sensors_generator:
                if hasattr(sensor_reading, 'name') and hasattr(sensor_reading, 'value'):
                    sensors[sensor_reading.name] = {
                        'value': getattr(sensor_reading, 'value', 0),
                        'units': getattr(sensor_reading, 'units', ''),
                        'type': getattr(sensor_reading, 'type', ''),
                        'health': getattr(sensor_reading, 'health', 'unknown'),
                        'imprecision': getattr(sensor_reading, 'imprecision', None),
                        'unavailable': getattr(sensor_reading, 'unavailable', False)
                    }
        except Exception as e:
            logger.warning(f"解析传感器数据时发生错误: {e}")
            return {}
        return sensors

    async def get_sensor_data(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """获取传感器数据"""
        port = self._ensure_port_is_int(port)
        try:
            conn = await self.pool.get_connection(ip, username, password, port)
            
            # 将整个阻塞的获取和迭代过程放入线程池
            sensors = await self._run_sync_ipmi(self._sync_fetch_and_parse_sensors, conn)

            sensor_data = {"temperature": [], "voltage": [], "fan_speed": [], "other": []}
            for sensor_name, sensor_info in sensors.items():
                if sensor_info.get('unavailable', False):
                    continue
                
                value = sensor_info.get('value', 0.0)
                try:
                    value = float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    value = 0.0

                sensor_entry = {
                    "name": sensor_name,
                    "value": value,
                    "unit": sensor_info.get('units', ''),
                    "status": sensor_info.get('health', 'unknown')
                }
                
                sensor_type = str(sensor_info.get('type', '')).lower()
                if 'temp' in sensor_type or 'thermal' in sensor_type:
                    sensor_data["temperature"].append(sensor_entry)
                elif 'voltage' in sensor_type or 'volt' in sensor_type:
                    sensor_data["voltage"].append(sensor_entry)
                elif 'fan' in sensor_type or 'rpm' in sensor_type:
                    sensor_data["fan_speed"].append(sensor_entry)
                else:
                    sensor_data["other"].append(sensor_entry)
            
            return sensor_data
            
        except IpmiException as e:
            logger.error(f"获取传感器数据失败 {ip}: {e}")
            raise IPMIError(f"获取传感器数据失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}: {e}")
            raise IPMIError(f"IPMI操作失败: {str(e)}")
    async def test_connection(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """测试IPMI连接"""
        port = self._ensure_port_is_int(port)
        try:
            conn = await self.pool.get_connection(ip, username, password, port)
            result = await self._run_sync_ipmi(conn.get_power)
            
            return {
                "status": "success",
                "message": "IPMI连接测试成功",
                "power_state": result.get('powerstate', 'unknown')
            }
            
        except (IpmiException, IPMIError) as e:
            logger.error(f"IPMI连接测试失败 {ip}: {e}")
            return {"status": "error", "message": f"IPMI连接失败: {str(e)}"}
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}: {e}")
            return {"status": "error", "message": f"IPMI操作失败: {str(e)}"}