import asyncio
import logging
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
        """获取IPMI连接"""
        connection_key = f"{ip}:{port}:{username}"
        
        async with self.semaphore:
            try:
                if connection_key not in self.connections:
                    # 创建新连接
                    conn = command.Command(
                        bmc=ip,
                        userid=username,
                        password=password,
                        port=port
                    )
                    self.connections[connection_key] = conn
                
                return self.connections[connection_key]
            except Exception as e:
                logger.error(f"创建IPMI连接失败: {e}")
                raise IPMIError(f"IPMI连接失败: {str(e)}")

# 全局连接池实例
ipmi_pool = IPMIConnectionPool(settings.IPMI_CONNECTION_POOL_SIZE)

class IPMIService:
    """IPMI服务"""
    
    def __init__(self):
        self.pool = ipmi_pool
    
    async def get_power_state(self, ip: str, username: str, password: str, port: int = 623) -> str:
        """获取电源状态"""
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
    
    async def get_system_info(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            conn = await self.pool.get_connection(ip, username, password, port)
            
            # 获取系统信息
            system_info = {}
            
            # 尝试获取设备ID
            try:
                device_id = conn.get_device_id()
                system_info.update({
                    "manufacturer": device_id.get('manufacturer', 'Unknown'),
                    "product": device_id.get('product', 'Unknown'),
                    "device_id": device_id.get('device_id', 'Unknown')
                })
            except:
                pass
            
            # 尝试获取BMC信息
            try:
                bmc_info = conn.get_bmc_netconfig()
                system_info.update({
                    "bmc_ip": bmc_info.get('ipaddr', ip),
                    "bmc_mac": bmc_info.get('macaddr', 'Unknown')
                })
            except:
                pass
            
            return system_info
            
        except IpmiException as e:
            logger.error(f"获取系统信息失败 {ip}: {e}")
            raise IPMIError(f"获取系统信息失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}: {e}")
            raise IPMIError(f"IPMI操作失败: {str(e)}")
    
    async def get_sensor_data(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """获取传感器数据"""
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