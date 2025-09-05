import asyncio
import logging
import ipaddress
import functools

from typing import Dict, Any, Optional
from pyghmi.ipmi import command
from pyghmi.exceptions import IpmiException

from app.core.config import settings
from app.core.exceptions import IPMIError

logger = logging.getLogger(__name__)

class IPMIConnectionPool:
    """IPMI连接池管理"""
    
    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self.connections = {}
        self.semaphore = asyncio.Semaphore(max_connections)
    
    async def get_connection(self, ip: str, username: str, password: str, port: int = 623):
        """获取IPMI连接（安全版，确保参数类型正确）"""
        # 确保参数类型
        try:
            ip = str(ip)
            port = int(port)
            # 如果 username 为 None，转换为空字符串
            username = str(username) if username is not None else ""
            # 如果 password 为 None，转换为空字符串
            password = str(password) if password is not None else ""
        except (ValueError, TypeError) as e:
            logger.error(f"IPMI连接参数类型无效: ip={ip}({type(ip)}), port={port}({type(port)}), "
                        f"user={username}({type(username)}), password={password}({type(password)})")
            raise IPMIError(f"IPMI连接参数类型错误: {e}")

        connection_key = f"{ip}:{port}:{username}"

        async with self.semaphore:
            try:
                # 使用 repr() 打印带引号的字符串，更容易区分空字符串和None
                logger.info(f"准备创建IPMI连接: bmc={repr(ip)}, port={port}, user={repr(username)}, password={repr(password)}")

                if connection_key not in self.connections:
                    # 创建新连接
                    conn = command.Command(
                        bmc=ip,
                        userid=username,
                        password=password, # 直接传递处理过的 password 字符串
                        port=port,
                        keepalive=True,
                        privlevel=4
                    )
                    self.connections[connection_key] = conn

                return self.connections[connection_key]

            except TypeError as e:
                # 捕获 pyghmi 内部类型错误
                logger.error(f"TypeError创建IPMI连接失败: {e}")
                logger.error(f"参数: bmc={repr(ip)}, port={repr(port)}, user={repr(username)}, password={repr(password)}")
                raise IPMIError(f"IPMI连接失败（类型错误）: {e}")

            except Exception as e:
                logger.error(f"创建IPMI连接失败: {e}")
                raise IPMIError(f"IPMI连接失败: {e}")

# 全局连接池实例
ipmi_pool = IPMIConnectionPool(settings.IPMI_CONNECTION_POOL_SIZE)

class IPMIService:
    """IPMI服务"""
    
    def __init__(self):
        self.pool = ipmi_pool
    
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
        # 确保端口是整数类型
        port = self._ensure_port_is_int(port)
        
        try:
            conn = await self.pool.get_connection(ip, username, password, port)
            result = conn.get_power()
            return result.get('powerstate', 'unknown')
        except IpmiException as e:
            logger.error(f"获取电源状态失败 {ip}: {e}")
            raise IPMIError(f"获取电源状态失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}: {e}")
            raise IPMIError(f"IPMI操作失败: {str(e)}")
    
    async def power_control(self, ip: str, username: str, password: str, action: str, port: int = 623) -> Dict[str, Any]:
        """电源控制"""
        # 确保端口是整数类型
        port = self._ensure_port_is_int(port)
        
        try:
            conn = await self.pool.get_connection(ip, username, password, port)
            
            # 映射电源操作
            power_actions = {
                'on': 'on',
                'off': 'off',
                'restart': 'reset',
                'force_off': 'off'
            }
            
            if action not in power_actions:
                raise IPMIError(f"不支持的电源操作: {action}")
            
            result = conn.set_power(power_actions[action])
            
            return {
                "action": action,
                "result": "success",
                "message": f"电源{action}操作成功"
            }
            
        except IpmiException as e:
            logger.error(f"电源控制失败 {ip} {action}: {e}")
            raise IPMIError(f"电源控制失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip} {action}: {e}")
            raise IPMIError(f"IPMI操作失败: {str(e)}")
    
    async def get_system_info(self, ip: str, username: str, password: str, port: int = 623, timeout: int = 10) -> Dict[str, Any]:
        """获取系统信息"""
        # 确保端口是整数类型
        port = self._ensure_port_is_int(port)
        timeout = self._ensure_port_is_int(timeout)
        try:
            logger.info(f"开始获取系统信息: {ip}:{port} 用户:{username}")
            
            # 使用超时控制
            async def _get_info():
                logger.info(f"创建IPMI连接: {ip}:{port} 用户:{username}")
                conn = await self.pool.get_connection(ip, username, password, port)
                
                # 获取系统信息
                system_info = {}
                
                # 尝试获取设备ID
                try:
                    logger.info(f"获取设备ID: {ip}:{port}")
                    device_id = conn.get_device_id()
                    logger.info(f"获取设备ID: {ip}:{port}")

                    system_info.update({
                        "manufacturer": device_id.get('manufacturer', 'Unknown'),
                        "product": device_id.get('product', 'Unknown'),
                        "device_id": device_id.get('device_id', 'Unknown'),
                        "serial": device_id.get('product_serial', 'Unknown')
                    })
                    logger.info(f"设备ID获取成功: {ip}:{port} 制造商:{device_id.get('manufacturer', 'Unknown')}")
                except Exception as e:
                    logger.debug(f"获取设备ID失败 {ip}:{port}: {e}")
                
                # 尝试获取BMC信息
                try:
                    logger.debug(f"获取BMC网络配置: {ip}:{port}")
                    bmc_info = conn.get_bmc_netconfig()
                    system_info.update({
                        "bmc_ip": bmc_info.get('ipaddr', ip),
                        "bmc_mac": bmc_info.get('macaddr', 'Unknown')
                    })
                    logger.debug(f"BMC网络配置获取成功: {ip}:{port}")
                except Exception as e:
                    logger.debug(f"获取BMC信息失败 {ip}:{port}: {e}")
                
                # 尝试获取BMC版本
                try:
                    logger.debug(f"获取BMC固件版本: {ip}:{port}")
                    fw_version = conn.get_firmware_version()
                    if fw_version:
                        system_info["bmc_version"] = str(fw_version)
                        logger.debug(f"BMC固件版本获取成功: {ip}:{port} 版本:{fw_version}")
                except Exception as e:
                    logger.debug(f"获取BMC版本失败 {ip}:{port}: {e}")
                
                logger.debug(f"系统信息获取完成: {ip}:{port}")
                return system_info
            
            # 使用超时控制
            result = await asyncio.wait_for(_get_info(), timeout=timeout)
            logger.debug(f"系统信息获取成功: {ip}:{port}")
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"获取系统信息超时 {ip}:{port}")
            raise IPMIError("获取系统信息超时")
        except IpmiException as e:
            logger.error(f"获取系统信息失败 {ip}:{port}: {e}")
            raise IPMIError(f"获取系统信息失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}:{port}: {e}")
            raise IPMIError(f"IPMI操作失败: {str(e)}")
    
    async def get_sensor_data(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """获取传感器数据"""
        # 确保端口是整数类型
        port = self._ensure_port_is_int(port)
        
        try:
            conn = await self.pool.get_connection(ip, username, password, port)
            
            # 获取传感器数据 - pyghmi返回的是生成器，需要转换为字典
            sensors_generator = conn.get_sensor_data()
            sensors = {}
            
            # 将生成器转换为字典
            try:
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
                logger.warning(f"解析传感器数据失败 {ip}: {e}")
                # 如果解析失败，返回空数据
                sensors = {}
            
            # 整理传感器数据
            sensor_data = {
                "temperature": [],
                "voltage": [],
                "fan_speed": [],
                "other": []
            }
            
            for sensor_name, sensor_info in sensors.items():
                # 检查传感器是否可用
                if sensor_info.get('unavailable', False):
                    continue
                    
                sensor_type = str(sensor_info.get('type', '')).lower()
                value = sensor_info.get('value', 0)
                unit = sensor_info.get('units', '')
                
                # 确保 value 是数值类型
                try:
                    if value is not None:
                        value = float(value)
                    else:
                        value = 0.0
                except (ValueError, TypeError):
                    value = 0.0
                
                sensor_entry = {
                    "name": sensor_name,
                    "value": value,
                    "unit": unit,
                    "status": sensor_info.get('health', 'unknown')
                }
                
                # 根据传感器类型分类
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
        # 确保端口是整数类型
        port = self._ensure_port_is_int(port)
        
        try:
            conn = await self.pool.get_connection(ip, username, password, port)
            
            # 尝试简单的操作来测试连接
            result = conn.get_power()
            
            return {
                "status": "success",
                "message": "IPMI连接测试成功",
                "power_state": result.get('powerstate', 'unknown')
            }
            
        except IpmiException as e:
            logger.error(f"IPMI连接测试失败 {ip}: {e}")
            return {
                "status": "error",
                "message": f"IPMI连接失败: {str(e)}"
            }
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}: {e}")
            return {
                "status": "error",
                "message": f"IPMI操作失败: {str(e)}"
            }