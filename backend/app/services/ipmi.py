import asyncio
import json
import logging
import ipaddress
import functools
import time
import concurrent.futures
from typing import Dict, Any, Optional, Generator, List
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
                # 为现有连接也更新超时设置
                existing_conn = self.connections[connection_key]
                # 注意：pyghmi的Command对象不支持动态修改超时，所以我们只能复用连接
                return existing_conn

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
        # 为同步IPMI操作设置超时
        return await asyncio.wait_for(loop.run_in_executor(None, partial_func), timeout=settings.IPMI_TIMEOUT)

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
            start_time = time.time()
            logger.debug(f"[电源状态] 开始获取电源状态: {ip}:{port}")
            conn = await self.pool.get_connection(ip, username, password, port, timeout=settings.IPMI_TIMEOUT)
            result = await self._run_sync_ipmi(conn.get_power)
            execution_time = time.time() - start_time
            logger.debug(f"[电源状态] 获取电源状态完成: {ip}:{port}, 耗时: {execution_time:.3f}秒")
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
            start_time = time.time()
            logger.debug(f"[电源控制] 开始电源控制操作: {ip}:{port}, 操作: {action}")
            conn = await self.pool.get_connection(ip, username, password, port, timeout=settings.IPMI_TIMEOUT)
            
            power_actions = {'on': 'on', 'off': 'off', 'restart': 'reset', 'force_off': 'off', 'force_restart': 'cycle'}
            if action not in power_actions:
                raise IPMIError(f"不支持的电源操作: {action}")
            
            await self._run_sync_ipmi(conn.set_power, power_actions[action])
            
            execution_time = time.time() - start_time
            logger.debug(f"[电源控制] 电源控制操作完成: {ip}:{port}, 操作: {action}, 耗时: {execution_time:.3f}秒")
            
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
                        # 尝试检测是否为UTF-8编码的乱码
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

            execution_time = time.time() - start_time
            logger.info(f"[系统信息] 系统信息获取成功: {ip}:{port} - {final_info}, 耗时: {execution_time:.3f}秒")
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
        """同步函数：并发获取并解析所有传感器数据。此函数将在线程池中运行。"""
        start_time = time.time()
        logger.debug(f"[传感器数据] 开始并发获取并解析传感器数据")
        sensors = {}
        try:
            # 记录 get_sensor_data() 调用的用时
            get_sensor_start = time.time()
            sensors_list = list(conn.get_sensor_data())
            get_sensor_time = time.time() - get_sensor_start
            logger.debug(f"[传感器数据] conn.get_sensor_data() 调用耗时: {get_sensor_time:.3f}秒, 共获取 {len(sensors_list)} 个传感器")
            
            # 使用线程池并发获取所有传感器的实时读数
            MAX_WORKERS = 32  # 设置并发线程数
            slow_sensors = []
            
            def read_sensor_value(sensor):
                """在新线程中读取传感器值和状态"""
                try:
                    # 访问 .value 触发实际的IPMI调用
                    current_value = sensor.value
                    
                    # 从内部的 ._reading 对象中获取 health 属性
                    current_health = "Unknown"
                    if hasattr(sensor, '_reading') and sensor._reading:
                        current_health = getattr(sensor._reading, 'health', 'Unknown')
                    
                    # 获取其他传感器属性
                    units = getattr(sensor, 'units', '')
                    sensor_type = getattr(sensor, 'type', '')
                    imprecision = getattr(sensor, 'imprecision', None)
                    unavailable = getattr(sensor, 'unavailable', False)
                    
                    return sensor.name, {
                        'value': current_value,
                        'units': units,
                        'type': sensor_type,
                        'health': current_health,
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
            
            # 使用线程池并发执行传感器读取
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                results = executor.map(read_sensor_value, sensors_list)
            
            # 处理并发执行结果
            for name, sensor_info in results:
                sensors[name] = sensor_info
                # 记录无效或异常的传感器
                if sensor_info.get('unavailable', False) or sensor_info.get('health', '').startswith('Error'):
                    slow_sensors.append(name)
                        
        except Exception as e:
            logger.warning(f"解析传感器数据时发生错误: {e}")
            return {}
        
        execution_time = time.time() - start_time
        if slow_sensors:
            logger.debug(f"[传感器数据] 检测到异常传感器: {', '.join(slow_sensors)}")
        logger.debug(f"[传感器数据] 并发获取并解析传感器数据完成, 共获取 {len(sensors)} 个传感器, 耗时: {execution_time:.3f}秒")
        return sensors

    async def get_sensor_data(self, ip: str, username: str, password: str, port: int = 623) -> Dict[str, Any]:
        """获取传感器数据"""
        port = self._ensure_port_is_int(port)
        try:
            start_time = time.time()
            logger.debug(f"[传感器采集] 开始采集传感器数据: {ip}:{port}")
            conn = await self.pool.get_connection(ip, username, password, port, timeout=settings.IPMI_TIMEOUT)
            
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
            
            execution_time = time.time() - start_time
            logger.debug(f"[传感器采集] 传感器数据采集完成: {ip}:{port}, 耗时: {execution_time:.3f}秒")
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