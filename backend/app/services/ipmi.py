import asyncio
import json
import logging
import ipaddress
import functools
import time
import concurrent.futures
from typing import Dict, Any, Optional, Generator, List

import httpx
from pyghmi.ipmi import command
from pyghmi.exceptions import IpmiException
from pyghmi.ipmi.sdr import SensorReading
import redfish

from app.core.config import settings
from app.core.exceptions import IPMIError

logger = logging.getLogger(__name__)

# 创建全局线程池用于传感器数据读取，提高性能
SENSOR_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=32)

class IPMIConnectionPool:
    """IPMI连接池管理"""
    
    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self.connections = {}
        self.semaphore = asyncio.Semaphore(max_connections)
    
    def _is_connection_valid(self, conn) -> bool:
        """检查IPMI连接是否仍然有效"""
        logger.debug(f"[IPMI连接] 开始检查连接有效性: {conn}")
        try:
            # 检查连接对象是否存在
            if conn is None:
                logger.debug("[IPMI连接] 连接对象为None")
                return False
            
            # 检查连接对象是否有ipmi_session属性
            if hasattr(conn, 'ipmi_session') and conn.ipmi_session is not None:
                logger.debug("[IPMI连接] 检查ipmi_session属性")
                # 检查ipmi_session是否标记为broken
                ipmi_session = conn.ipmi_session
                if hasattr(ipmi_session, 'broken'):
                    is_broken = bool(ipmi_session.broken)
                    logger.debug(f"[IPMI连接] ipmi_session.broken返回: {is_broken}")
                    if is_broken:
                        logger.debug("[IPMI连接] ipmi_session.broken为True，连接已断开")
                        return False
            elif hasattr(conn, 'ipmi_session'):
                # ipmi_session属性存在但为None
                logger.debug("[IPMI连接] ipmi_session属性为None")
                return False
            
            # 如果所有检查都通过，认为连接是有效的
            logger.debug("[IPMI连接] 连接检查通过，连接有效")
            return True
            
        except Exception as e:
            logger.debug(f"[IPMI连接] 检查连接有效性时出错: {e}")
            return False
        finally:
            logger.debug("[IPMI连接] 连接有效性检查完成")
    
    async def get_connection(self, ip: str, username: str, password: str, port: int = 623, timeout: int = 30):
        """获取IPMI连接（安全版，带超时保护，避免在OpenBMC卡死）"""
        # 使用配置的超时值作为默认值
        if timeout == 30:  # 如果使用默认值，则使用配置的超时值
            timeout = settings.IPMI_TIMEOUT
            
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
                # 检查现有连接是否仍然有效
                existing_conn = self.connections[connection_key]
                if self._is_connection_valid(existing_conn):
                    # 注意：pyghmi的Command对象不支持动态修改超时，所以我们只能复用连接
                    return existing_conn
                else:
                    # 连接已失效，从连接池中移除
                    logger.debug(f"[IPMI连接] 移除失效连接: {connection_key}")
                    self.connections.pop(connection_key, None)
                    # 关闭失效连接，退出登录以清理pyghmi缓存
                    try:
                        if hasattr(existing_conn, 'ipmi_session'):
                            # 1. 欺骗 pyghmi，让它以为连接是好的
                            existing_conn.ipmi_session.broken = False 
                            # 2. 欺骗 pyghmi，让它以为已经登出了(避免发包报错)，直接进清理流程
                            existing_conn.ipmi_session.logged = 0                                 
                            existing_conn.ipmi_session.logout()
                            logger.debug(f"[IPMI连接] logout成功: {connection_key}")
                    except Exception as e:
                        logger.debug(f"[IPMI连接] 关闭失效连接时logout出错: {e}")

            loop = asyncio.get_running_loop()
            
            start_time = time.time()
            logger.debug(f"[IPMI连接] 开始创建连接: {ip}:{port}")

            def _make_conn():
                # 在创建连接时设置超时参数
                return command.Command(
                    bmc=ip,
                    userid=username,
                    password=password,
                    port=port,
                    keepalive=True,
                    interface="lanplus",
                    privlevel=4,
                    # 注意：pyghmi的Command构造函数不直接支持timeout参数
                    # 超时控制主要通过外部的asyncio.wait_for实现
                )

            try:
                # 在子线程里跑，并设置超时
                conn = await asyncio.wait_for(loop.run_in_executor(None, _make_conn), timeout=timeout)
                connection_time = time.time() - start_time
                logger.debug(f"[IPMI连接] 连接创建成功: {ip}:{port}, 耗时: {connection_time:.3f}秒")
                self.connections[connection_key] = conn
                return conn
            except asyncio.TimeoutError:
                connection_time = time.time() - start_time
                logger.error(f"[IPMI连接] 创建连接超时: {ip}:{port}, 耗时: {connection_time:.3f}秒")
                raise IPMIError(f"IPMI连接超时: {ip}:{port}")
            except Exception as e:
                connection_time = time.time() - start_time
                logger.error(f"[IPMI连接] 创建连接失败: {ip}:{port}, 耗时: {connection_time:.3f}秒, 错误: {e}")
                raise IPMIError(f"IPMI连接失败: {e}")

    def close(self):
        """关闭连接池并清理资源"""
        # 清理所有连接
        for conn_key, conn in self.connections.items():
            try:
                if hasattr(conn, 'close'):
                    conn.close()
            except Exception as e:
                logger.error(f"关闭IPMI连接 {conn_key} 时出错: {e}")
        
        self.connections.clear()

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
        # 移除外层的asyncio.wait_for包装，让IPMI调用自主管理超时
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
        start_time = time.time()
        try:
            logger.debug(f"[电源状态] 开始获取电源状态: {ip}:{port}")
            conn = await self.pool.get_connection(ip, username, password, port, timeout=settings.IPMI_TIMEOUT)
            result = await self._run_sync_ipmi(conn.get_power)
            execution_time = time.time() - start_time
            logger.debug(f"[电源状态] 获取电源状态完成: {ip}:{port}, 耗时: {execution_time:.3f}秒")
            return result.get('powerstate', 'unknown')
        except IpmiException as e:
            execution_time = time.time() - start_time
            logger.error(f"获取电源状态失败 {ip}: {e}")
            raise IPMIError(f"获取电源状态失败: {str(e)}")
        except Exception as e:
            execution_time = time.time() - start_time
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
        start_time = time.time()
        # 定义电源操作映射
        power_actions = {'on': 'on', 'off': 'off', 'restart': 'reset', 'force_off': 'off', 'force_restart': 'cycle'}
        
        try:
            logger.debug(f"[电源控制] 开始电源控制操作: {ip}:{port}, 操作: {action}")
            conn = await self.pool.get_connection(ip, username, password, port, timeout=settings.IPMI_TIMEOUT)
            
            if action not in power_actions:
                raise IPMIError(f"不支持的电源操作: {action}")
            
            await self._run_sync_ipmi(conn.set_power, power_actions[action])
            
            execution_time = time.time() - start_time
            logger.debug(f"[电源控制] 电源控制操作完成: {ip}:{port}, 操作: {action}, 耗时: {execution_time:.3f}秒")
            
            return {"action": action, "result": "success", "message": f"电源{action}操作成功"}
            
        except IpmiException as e:
            execution_time = time.time() - start_time
            logger.error(f"电源控制失败 {ip} {action}: {e}")
            raise IPMIError(f"电源控制失败: {str(e)}")
        except Exception as e:
            execution_time = time.time() - start_time
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
        支持多种FRU格式，包括您提供的格式。
        """
        results = {}

        # 1. 获取系统清单 (FRU, 固件版本等)
        try:
            # get_inventory() 是一个生成器，我们需要查找包含FRU信息的组件
            inventory_generator = conn.get_inventory()
            
            # 查找包含制造商信息的组件（可能是System、system、主板等）
            system_info = None
            system_name = None
            
            for name, info in inventory_generator:
                logger.info(f"get_inventory() 组件: {name}, 类型: {type(info)}")
                if isinstance(info, dict):
                    # 检查是否有制造商信息
                    if (info.get('Manufacturer') or info.get('Board manufacturer') or 
                        info.get('Product name') or info.get('Board product name')):
                        system_name = name
                        system_info = info
                        logger.info(f"找到包含FRU信息的组件: {name}")
                        logger.info(f"FRU数据内容: {json.dumps(info, indent=2, ensure_ascii=False)}")
                        break
            
            # 如果没有找到有信息的组件，尝试第一个组件
            if not system_info:
                inventory_generator = conn.get_inventory()  # 重新获取生成器
                system_name, system_info = next(inventory_generator)
                logger.info(f"使用第一个组件: system_name={system_name}")

            if system_info and isinstance(system_info, dict):
                # 根据实际返回的扁平化数据结构来提取信息
                # 实际的FRU数据是扁平化的，直接包含各个字段
                
                # 尝试多种可能的制造商字段名（扁平化结构）
                manufacturer = (system_info.get('Manufacturer') or 
                             system_info.get('Board manufacturer') or 
                             system_info.get('Mfg') or 
                             system_info.get('Vendor') or 
                             'Unknown')
                
                # 处理None值：如果制造商为None，则使用Unknown
                if manufacturer is None:
                    manufacturer = 'Unknown'
                
                # 智能推断：如果制造商仍然是Unknown，尝试从其他字段推断
                if manufacturer == 'Unknown':
                    # 尝试从产品型号或序列号推断
                    product_name = (system_info.get('Product name') or 
                                 system_info.get('Board product name') or 
                                 system_info.get('Product') or 
                                 system_info.get('Model') or 
                                 '')
                    
                    # 从序列号或产品特征推断
                    serial_num = (system_info.get('Serial Number') or 
                                 system_info.get('Board serial number') or 
                                 system_info.get('Chassis serial number') or 
                                 '')
                    
                    # 根据常见的产品特征进行推断
                    if product_name:
                        product_lower = product_name.lower()
                        if 'dell' in product_lower or 'poweredge' in product_lower:
                            manufacturer = 'Dell'
                        elif 'hp' in product_lower or 'proliant' in product_lower:
                            manufacturer = 'HPE'
                        elif 'lenovo' in product_lower:
                            manufacturer = 'Lenovo'
                        elif 'huawei' in product_lower:
                            manufacturer = 'Huawei'
                        elif 'inspur' in product_lower:
                            manufacturer = 'Inspur'
                        elif 'h3c' in product_lower:
                            manufacturer = 'H3C'
                        elif 'sugon' in product_lower or 'dawning' in product_lower:
                            manufacturer = 'Sugon'
                        elif '4u' in product_lower or '2u' in product_lower or '1u' in product_lower:
                            # 如果是机架式服务器但没有明确品牌，标记为通用服务器
                            manufacturer = 'Generic Server'
                    
                    # 如果还是Unknown，使用产品名称作为线索
                    if manufacturer == 'Unknown' and product_name:
                        manufacturer = f'Unknown ({product_name})'
                    elif manufacturer == 'Unknown' and serial_num:
                        manufacturer = f'Unknown (SN: {serial_num[:8]}...)'
                
                # 尝试多种可能的产品名字段（扁平化结构）
                product = (system_info.get('Product name') or 
                          system_info.get('Board product name') or 
                          system_info.get('Product') or 
                          system_info.get('Model') or 
                          'Unknown')
                
                # 处理中文编码问题：检测并修复乱码
                def fix_encoding(text):
                    """修复可能的编码问题"""
                    if not text or text == 'Unknown' or text is None:
                        return text
                    
                    # 检测是否为乱码（包含典型的UTF-8解码错误模式）
                    try:
                        # 尝试检测是否为UTF-8被错误解码为Latin-1的乱码
                        if 'å' in text or '¤' in text or 'æ' in text:
                            # 可能是UTF-8被错误解码为Latin-1的乱码
                            # 尝试重新编码为Latin-1，然后解码为UTF-8
                            try:
                                fixed = text.encode('latin-1').decode('utf-8')
                                return fixed
                            except (UnicodeEncodeError, UnicodeDecodeError):
                                pass
                        
                        # 尝试其他常见的编码修复
                        try:
                            # 尝试GBK编码
                            fixed = text.encode('latin-1').decode('gbk')
                            return fixed
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            pass
                            
                        try:
                            # 尝试GB2312编码
                            fixed = text.encode('latin-1').decode('gb2312')
                            return fixed
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            pass
                    except Exception:
                        pass
                    
                    return text
                
                # 修复制造商和产品名称的编码
                manufacturer = fix_encoding(manufacturer)
                product = fix_encoding(product)
                
                # 尝试多种可能的序列号字段（扁平化结构）
                serial = (system_info.get('Serial Number') or 
                         system_info.get('Board serial number') or 
                         system_info.get('Chassis serial number') or 
                         system_info.get('Serial') or 
                         'Unknown')
                
                # 尝试多种可能的固件版本字段（扁平化结构）
                bmc_version = (system_info.get('firmware_version') or 
                              system_info.get('Firmware Version') or 
                              system_info.get('Version') or 
                              system_info.get('Hardware Version') or 
                              'Unknown')

                results['manufacturer'] = manufacturer
                results['product'] = product
                results['serial'] = serial
                results['bmc_version'] = bmc_version
                
                logger.info(f"成功解析系统清单: manufacturer={manufacturer}, product={product}, serial={serial}, bmc_version={bmc_version}")
                logger.debug(f"完整的FRU数据: {system_info}")
            else:
                logger.warning(f"get_inventory() 返回非预期格式: system_name={system_name}, system_info类型={type(system_info)}")

        except StopIteration:
            logger.warning(f"获取系统清单失败: get_inventory() 未返回任何信息。这可能是BMC未实现FRU功能或权限不足。尝试使用备用方法获取基本信息...")
            # 备用方法：尝试通过其他方式获取基本信息
            try:
                # 尝试获取BMC信息作为备用
                bmc_info = conn.get_bmc_configuration()
                if bmc_info:
                    results['manufacturer'] = bmc_info.get('manufacturer', 'Unknown')
                    results['product'] = bmc_info.get('product_name', 'Unknown')
                    results['bmc_version'] = bmc_info.get('firmware_version', 'Unknown')
                    logger.info(f"使用备用方法获取BMC信息: {results}")
            except Exception as backup_e:
                logger.warning(f"备用方法也失败: {backup_e}")
        except Exception as e:
            logger.warning(f"同步获取系统清单时发生错误: {e}")

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
        # 使用配置的超时值
        timeout = settings.IPMI_TIMEOUT
        try:
            start_time = time.time()
            logger.info(f"[系统信息] 开始获取系统信息: {ip}:{port} 用户:{username}")
            
            conn = await self.pool.get_connection(ip, username, password, port, timeout=timeout)
            
            # 在线程池中执行所有同步操作
            # 移除外层的asyncio.wait_for包装，让IPMI调用自主管理超时
            system_info = await self._run_sync_ipmi(self._sync_get_all_info, conn, ip)
            
            # 为未获取到的信息提供默认值
            final_info = {
                "manufacturer": system_info.get('manufacturer', 'Unknown'),
                "product": system_info.get('product', 'Unknown'),
                "serial": system_info.get('serial', 'Unknown'),
                "bmc_ip": system_info.get('bmc_ip', ip),
                "bmc_mac": system_info.get('bmc_mac', 'Unknown'),
                "bmc_version": system_info.get('bmc_version', 'Unknown'),
            }

            execution_time = time.time() - start_time
            logger.info(f"[系统信息] 系统信息获取成功: {ip}:{port} - {final_info}, 耗时: {execution_time:.3f}秒")
            return final_info
            
        except IpmiException as e:
            logger.error(f"获取系统信息失败 {ip}:{port}: {e}")
            raise IPMIError(f"获取系统信息失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}:{port}: {e}", exc_info=True)
            raise IPMIError(f"IPMI操作失败: {str(e)}")

    def _sync_read_sensor_value(self, sensor):
        """
        在线程池中执行的同步函数：读取单个传感器的值
        这是优化后的传感器读取函数，参考了高效示例的实现
        """
        try:
            # 访问 .value 触发实际的IPMI调用
            value = sensor.value
            
            # 从内部的 ._reading 对象中获取 health 属性
            health = "Unknown"
            if hasattr(sensor, '_reading') and sensor._reading:
                health = getattr(sensor._reading, 'health', 'Unknown')
            
            # 获取其他传感器属性
            units = getattr(sensor, 'units', '')
            sensor_type = getattr(sensor, 'type', '')
            imprecision = getattr(sensor, 'imprecision', None)
            unavailable = getattr(sensor, 'unavailable', False)
            
            return sensor.name, {
                'value': value,
                'units': units,
                'type': sensor_type,
                'health': health,
                'imprecision': imprecision,
                'unavailable': unavailable
            }
        except Exception as e:
            return sensor.name, {
                'value': None,
                'units': '',
                'type': '',
                'health': f"Error: {e}",
                'imprecision': None,
                'unavailable': True
            }

    async def _async_get_sensor_data(self, sensor, conn, timeout=10):
        """
        异步获取单个传感器数据
        参考高效示例实现，为每个传感器设置独立的超时控制
        """
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(SENSOR_EXECUTOR, self._sync_read_sensor_value, sensor),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return sensor.name, {
                'value': None,
                'units': '',
                'type': '',
                'health': f"Timeout: > {timeout}s",
                'imprecision': None,
                'unavailable': True
            }
        except Exception as e:
            return sensor.name, {
                'value': None,
                'units': '',
                'type': '',
                'health': f"Error: {e}",
                'imprecision': None,
                'unavailable': True
            }

    async def get_sensor_data(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """获取传感器数据"""
        port = self._ensure_port_is_int(port)
        try:
            start_time = time.time()
            logger.debug(f"[传感器采集] 开始采集传感器数据: {ip}:{port}")
            
            # 连接耗时
            connect_start = time.time()
            conn = await self.pool.get_connection(ip, username, password, port, timeout=settings.IPMI_TIMEOUT)
            connect_time = time.time() - connect_start
            logger.debug(f"[传感器采集] IPMI连接完成: {ip}:{port}, 耗时: {connect_time:.3f}秒")
            
            # 获取传感器列表耗时
            sensors_start = time.time()
            sensors_list = list(conn.get_sensor_data())
            sensors_time = time.time() - sensors_start
            logger.debug(f"[传感器采集] 获取传感器列表完成，共 {len(sensors_list)} 个传感器, 耗时: {sensors_time:.3f}秒")
            
            # 传感器去重耗时
            unique_start = time.time()
            unique_sensors = {}
            for sensor in sensors_list:
                if sensor.name not in unique_sensors:
                    unique_sensors[sensor.name] = sensor
            sensors_list = list(unique_sensors.values())
            unique_time = time.time() - unique_start
            logger.debug(f"[传感器采集] 去重后剩余 {len(sensors_list)} 个传感器, 耗时: {unique_time:.3f}秒")
            
            # 异步并发获取所有传感器数据耗时
            fetch_start = time.time()
            tasks = [self._async_get_sensor_data(sensor, conn, timeout=10) for sensor in sensors_list]
            results = await asyncio.gather(*tasks)
            fetch_time = time.time() - fetch_start
            logger.debug(f"[传感器采集] 并发获取传感器数据完成, 耗时: {fetch_time:.3f}秒, 有效传感器: {len(results)}个")
            
            # 数据处理和分类耗时
            process_start = time.time()
            sensor_data = {"temperature": [], "voltage": [], "fan_speed": [], "other": []}
            valid_sensors = 0
            for name, sensor_info in results:
                if sensor_info.get('unavailable', False):
                    continue
                
                value = sensor_info.get('value', 0.0)
                try:
                    value = float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    value = 0.0

                sensor_entry = {
                    "name": name,
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
                valid_sensors += 1
            
            process_time = time.time() - process_start
            execution_time = time.time() - start_time
            logger.debug(f"[传感器采集] 传感器数据处理完成, 有效传感器: {valid_sensors}个, 耗时: {process_time:.3f}秒")
            logger.debug(f"[传感器采集] 传感器数据采集完成: {ip}:{port}, 总耗时: {execution_time:.3f}秒, "
                        f"连接: {connect_time:.3f}s, 获取列表: {sensors_time:.3f}s, 去重: {unique_time:.3f}s, "
                        f"并发读取: {fetch_time:.3f}s, 处理: {process_time:.3f}s")
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
            start_time = time.time()
            logger.debug(f"[连接测试] 开始测试IPMI连接: {ip}:{port}")
            conn = await self.pool.get_connection(ip, username, password, port, timeout=settings.IPMI_TIMEOUT)
            result = await self._run_sync_ipmi(conn.get_power)
            
            execution_time = time.time() - start_time
            logger.debug(f"[连接测试] IPMI连接测试完成: {ip}:{port}, 耗时: {execution_time:.3f}秒")
            
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
    
    async def get_users(self, ip: str, username: str, password: str, port: int = 623) -> List[Dict[str, Any]]:
        """获取BMC用户列表"""
        port = self._ensure_port_is_int(port)
        try:
            start_time = time.time()
            logger.debug(f"[用户列表] 开始获取用户列表: {ip}:{port}")
            conn = await self.pool.get_connection(ip, username, password, port, timeout=settings.IPMI_TIMEOUT)
            users = await self._run_sync_ipmi(conn.get_users)
            execution_time = time.time() - start_time
            logger.debug(f"[用户列表] 获取用户列表完成: {ip}:{port}, 用户数: {len(users)}, 耗时: {execution_time:.3f}秒")
            return users
        except IpmiException as e:
            logger.error(f"获取用户列表失败 {ip}: {e}")
            raise IPMIError(f"获取用户列表失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}: {e}")
            raise IPMIError(f"IPMI操作失败: {str(e)}")
    
    async def create_user(self, ip: str, admin_username: str, admin_password: str, 
                         new_userid: int, new_username: str, new_password: str, 
                         priv_level: str = 'user', port: int = 623) -> bool:
        """创建BMC用户"""
        port = self._ensure_port_is_int(port)
        try:
            start_time = time.time()
            logger.debug(f"[创建用户] 开始创建用户: {ip}:{port}, 用户名: {new_username}")
            conn = await self.pool.get_connection(ip, admin_username, admin_password, port, timeout=settings.IPMI_TIMEOUT)
            
            # 创建用户
            await self._run_sync_ipmi(
                conn.create_user,
                uid=new_userid,
                name=new_username,
                password=new_password,
                privilege_level=priv_level
            )
            
            execution_time = time.time() - start_time
            logger.info(f"[创建用户] 成功创建用户: {ip}:{port}, 用户名: {new_username}, 耗时: {execution_time:.3f}秒")
            return True
        except IpmiException as e:
            logger.error(f"创建用户失败 {ip}: {e}")
            raise IPMIError(f"创建用户失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}: {e}")
            raise IPMIError(f"IPMI操作失败: {str(e)}")
    
    async def set_user_priv(self, ip: str, admin_username: str, admin_password: str,
                           userid: int, priv_level: str, port: int = 623) -> bool:
        """设置用户权限级别"""
        port = self._ensure_port_is_int(port)
        try:
            start_time = time.time()
            logger.debug(f"[设置权限] 开始设置用户权限: {ip}:{port}, 用户ID: {userid}")
            conn = await self.pool.get_connection(ip, admin_username, admin_password, port, timeout=settings.IPMI_TIMEOUT)
            
            # 设置用户权限
            await self._run_sync_ipmi(
                conn.set_user_priv,
                uid=userid,
                privilege_level=priv_level
            )
            
            execution_time = time.time() - start_time
            logger.info(f"[设置权限] 成功设置用户权限: {ip}:{port}, 用户ID: {userid}, 权限: {priv_level}, 耗时: {execution_time:.3f}秒")
            return True
        except IpmiException as e:
            logger.error(f"设置用户权限失败 {ip}: {e}")
            raise IPMIError(f"设置用户权限失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}: {e}")
            raise IPMIError(f"IPMI操作失败: {str(e)}")
    
    async def set_user_password(self, ip: str, admin_username: str, admin_password: str,
                               userid: int, new_password: str, port: int = 623) -> bool:
        """设置用户密码"""
        port = self._ensure_port_is_int(port)
        try:
            start_time = time.time()
            logger.debug(f"[设置密码] 开始设置用户密码: {ip}:{port}, 用户ID: {userid}")
            conn = await self.pool.get_connection(ip, admin_username, admin_password, port, timeout=settings.IPMI_TIMEOUT)
            
            # 设置用户密码
            await self._run_sync_ipmi(
                conn.set_user_password,
                uid=userid,
                mode='set_password',
                password=new_password
            )
            
            execution_time = time.time() - start_time
            logger.info(f"[设置密码] 成功设置用户密码: {ip}:{port}, 用户ID: {userid}, 耗时: {execution_time:.3f}秒")
            return True
        except IpmiException as e:
            logger.error(f"设置用户密码失败 {ip}: {e}")
            raise IPMIError(f"设置用户密码失败: {str(e)}")
        except Exception as e:
            logger.error(f"IPMI操作异常 {ip}: {e}")
            raise IPMIError(f"IPMI操作失败: {str(e)}")
    
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
            conn = await self.pool.get_connection(ip, admin_username, admin_password, port)
            
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