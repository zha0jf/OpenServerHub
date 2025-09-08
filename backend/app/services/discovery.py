import asyncio
import socket
import ipaddress
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import logging
from sqlalchemy.orm import Session
import csv
import io
import struct
import traceback

from contextlib import closing

from app.services.ipmi import IPMIService
from app.services.server import ServerService
from app.schemas.server import ServerCreate
from app.models.server import Server
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class DiscoveryService:
    """设备发现服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ipmi_service = IPMIService()
        self.server_service = ServerService(db)
    
    async def scan_network_range(
        self, 
        network: str, 
        port: int = 623,
        timeout: int = 3,
        max_workers: int = 50
    ) -> List[Dict[str, Any]]:
        """
        扫描网络范围内的BMC设备
        
        Args:
            network: 网络范围，支持CIDR格式，如 "192.168.1.0/24" 或 "192.168.1.1-192.168.1.100"
            port: IPMI端口，默认623
            timeout: 超时时间（秒）
            max_workers: 最大并发数
        
        Returns:
            发现的设备列表
        """
        # 确保端口是整数类型（更严格的检查）
        try:
            if not isinstance(port, int):
                port = int(port)
        except (ValueError, TypeError) as e:
            logger.error(f"端口参数无法转换为整数: {port}, 类型: {type(port)}")
            raise ValidationError(f"端口参数无效: {port}")
        
        logger.info(f"开始扫描网络范围: {network}, 端口: {port}")
        
        # 解析网络范围
        ip_list = self._parse_network_range(network)
        if not ip_list:
            raise ValidationError("无效的网络范围格式")
        
        logger.info(f"将扫描 {len(ip_list)} 个IP地址")
        
        # 限制并发数量，避免网络拥堵
        semaphore = asyncio.Semaphore(min(max_workers, 50))
        
        # 创建扫描任务
        tasks = []
        for ip in ip_list:
            task = self._scan_single_ip(ip, port, timeout, semaphore)
            tasks.append(task)
        
        # 并发执行扫描
        results = []
        completed_count = 0
        
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result:
                    # 检查设备是否已存在于系统中
                    existing_server = self.server_service.get_server_by_ipmi_ip(result["ip"])
                    if existing_server:
                        result["already_exists"] = True
                        result["existing_server_id"] = existing_server.id
                        result["existing_server_name"] = existing_server.name
                    else:
                        result["already_exists"] = False
                        result["existing_server_id"] = None
                        result["existing_server_name"] = None
                    
                    results.append(result)
                completed_count += 1
                
                # 每扫描完成10个IP记录一次进度
                if completed_count % 10 == 0:
                    logger.info(f"扫描进度: {completed_count}/{len(ip_list)}, 已发现: {len(results)}")
                    
            except Exception as e:
                logger.warning(f"扫描任务异常: {str(e)}")
                completed_count += 1
        
        logger.info(f"网络扫描完成，共扫描 {len(ip_list)} 个IP，发现 {len(results)} 个BMC设备")
        return results

    async def _scan_single_ip(
        self, 
        ip: str, 
        port: int, 
        timeout: int, 
        semaphore: asyncio.Semaphore
    ) -> Optional[Dict[str, Any]]:
        """扫描单个IP地址"""
        # 确保端口是整数类型（额外检查）
        try:
            if not isinstance(port, int):
                port = int(port)
        except (ValueError, TypeError) as e:
            logger.error(f"端口参数无法转换为整数: {port}, 类型: {type(port)}")
            return None
        
        async with semaphore:
            try:
                logger.info(f"开始扫描IP: {ip}:{port}")
                
                # 首先进行端口连通性检查
                port_open = await self._check_port_open(ip, port, timeout)
                if not port_open:
                    logger.info(f"IP {ip}:{port} 端口未开放，跳过")
                    return None
                
                logger.info(f"IP {ip}:{port} 端口开放，开始探测BMC设备")
                
                # 尝试获取BMC设备信息
                device_info = await self._probe_bmc_device(ip, port, timeout)
                if device_info:
                    if device_info.get("accessible"):
                        logger.info(f"发现可访问的BMC设备: {ip}:{port} (制造商: {device_info.get('manufacturer', 'Unknown')})")
                    else:
                        logger.info(f"发现BMC设备但需要认证: {ip}:{port}")
                    return device_info
                else:
                    logger.info(f"IP {ip}:{port} 未发现BMC设备")
                
            except Exception as e:
                logger.warning(f"扫描IP {ip}:{port} 失败: {str(e)}")
            
            return None
    
    async def _check_udp_port(self, ip: str, port: int, timeout: int) -> bool:
        """异步检查 UDP 端口是否开放（通过 IPMI RMCP ping）"""
        loop = asyncio.get_running_loop()
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
            # asyncio 期望非阻塞套接字
            sock.setblocking(False)

            # 连接到目标，这样可以直接使用 sock_sendall / sock_recv
            try:
                sock.connect((ip, port))
            except OSError:
                return False

            # IPMI RMCP/ASF ping 固定 8 字节
            rmcp_ping = struct.pack('!BBBBBBBB', 0x06, 0x00, 0xFF, 0x06, 0x00, 0x00, 0x11, 0xBE)

            try:
                await loop.sock_sendall(sock, rmcp_ping)
                # fut = loop.sock_recv(sock, 1024)  # 等待对端回包
                # await asyncio.wait_for(fut, timeout=timeout)
                return True
            except (asyncio.TimeoutError, OSError):
                return False

    async def _check_tcp_port(self, ip: str, port: int, timeout: int) -> bool:
        """异步检查 TCP 端口是否开放"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _check_port_open(self, ip: str, port: int, timeout: int) -> bool:
        """检查端口是否开放（先TCP，再IPMI）"""
        # IPMI 默认 UDP 623，用 RMCP ping 试探
        ok = await self._check_tcp_port(ip, port, timeout)
        if ok:
            return True

        """使用 ipmitool mc ping 检查 IPMI 服务是否可连接（防止卡死）"""

        loop = asyncio.get_event_loop()

        def _run_ipmitool():
            try:
                proc = subprocess.Popen(
                    ["ipmitool", "-H", ip, "-I", "lanplus", "-U", "", "-P", "", "-p", str(port), "mc", "ping"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                try:
                    stdout, stderr = proc.communicate(timeout=timeout)
                    return True
                except subprocess.TimeoutExpired:
                    # 确保彻底杀掉进程
                    proc.kill()
                    try:
                        proc.communicate(timeout=1)
                    except Exception:
                        pass
                    return False
            except FileNotFoundError:
                logger.info("未找到 ipmitool，请确认已安装并在 PATH 中")
                return False
            except Exception as e:
                tb = traceback.format_exc()
                logger.info(f"IPMI mc ping 异常 {ip}:{port} -> {repr(e)}\n{tb}")
                return False

        try:
            # 外层再套一层 asyncio 超时控制，双保险
            return await asyncio.wait_for(loop.run_in_executor(None, _run_ipmitool), timeout=timeout+1)
        except asyncio.TimeoutError:
            logger.info(f"IPMI mc ping 超时(外层强杀) {ip}:{port}")
            return False
        except Exception as e:
            tb = traceback.format_exc()
            logger.info(f"IPMI mc ping 异常 {ip}:{port} -> {repr(e)}\n{tb}")
            return False

    async def _probe_bmc_device(self, ip: str, port: int, timeout: int) -> Optional[Dict[str, Any]]:
        """探测BMC设备信息"""
        try:
            # 使用常见的默认用户名密码尝试连接
            # 扩展凭据列表，支持更多厂商和OpenBMC
            common_credentials = [
                # 超微(Supermicro)
                ("root", "0penBmc"),
                ("ADMIN", "ADMIN"),
                ("ADMIN", "Test@123123"),
                ("Administrator", "superuser"),

                # OpenBMC / 通用

                # 浪潮(Inspur)
                ("root", "superuser"),

                # 华为(Huawei)
                ("Administrator", "Admin@9000"),
                ("root", "Huawei12#$"),

                # 通用默认
                ("", ""),  # 无认证


            ]
            
            port = int(port)
            timeout = int(timeout)

            logger.info(f"开始探测BMC设备 {ip}:{port}，尝试 {len(common_credentials)} 组凭据")
            
            for i, (username, password) in enumerate(common_credentials):
                try:
                    logger.info(f"[{i+1}/{len(common_credentials)}] 尝试凭据 {username}:{'*'*len(password) if password else '(空)'} 连接 {ip}:{port}")
                    
                    # 尝试获取系统信息
                    system_info = await self.ipmi_service.get_system_info(
                        ip=ip,
                        username=username,
                        password=password,
                        port=port,
                        timeout=timeout
                    )
                    
                    if system_info:
                        logger.info(f"凭据测试成功: {ip}:{port} 使用 {username}:{'*'*len(password) if password else '(空)'}")
                        return {
                            "ip": ip,
                            "port": port,
                            "username": username,
                            "password": password,
                            "manufacturer": system_info.get("manufacturer", ""),
                            "model": system_info.get("product", ""),
                            "serial_number": system_info.get("serial", ""),
                            "bmc_version": system_info.get("bmc_version", ""),
                            "accessible": True,
                            "auth_required": bool(username or password)
                        }
                        
                except Exception as e:
                    logger.debug(f"尝试凭据 {username}:{'*'*len(password) if password else '(空)'} 连接 {ip}:{port} 失败: {str(e)}")
                    continue
            
            # 如果所有凭据都失败，但端口开放，返回基本信息
            logger.info(f"BMC设备探测完成但未找到有效凭据: {ip}:{port}")
            return {
                "ip": ip,
                "port": port,
                "username": "",
                "password": "",
                "manufacturer": "",
                "model": "",
                "serial_number": "",
                "bmc_version": "",
                "accessible": False,
                "auth_required": True
            }
            
        except Exception as e:
            logger.warning(f"探测BMC设备 {ip}:{port} 失败: {str(e)}")
            return None
    
    def _parse_network_range(self, network: str) -> List[str]:
        """解析网络范围"""
        ip_list = []
        
        try:
            if "/" in network:
                # CIDR格式: 192.168.1.0/24
                network_obj = ipaddress.IPv4Network(network, strict=False)
                # 排除网络地址和广播地址
                ip_list = [str(ip) for ip in network_obj.hosts()]
            elif "-" in network:
                # 范围格式: 192.168.1.1-192.168.1.100
                start_ip, end_ip = network.split("-", 1)
                start_ip = start_ip.strip()
                end_ip = end_ip.strip()
                
                start = ipaddress.IPv4Address(start_ip)
                end = ipaddress.IPv4Address(end_ip)
                
                if start > end:
                    raise ValueError("起始IP不能大于结束IP")
                
                start_int = int(start)
                end_int = int(end)
                for val in range(start_int, end_int + 1):
                    ip_list.append(str(ipaddress.IPv4Address(val)))
            else:
                # 单个IP地址
                ipaddress.IPv4Address(network)  # 验证IP格式
                ip_list = [network]
                
        except Exception as e:
            logger.error(f"解析网络范围失败: {network}, 错误: {str(e)}")
            return []
        
        return ip_list
    
    async def batch_import_servers(
        self, 
        discovered_devices: List[Dict[str, Any]],
        default_username: str = "",
        default_password: str = "",
        group_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        批量导入发现的服务器
        
        Args:
            discovered_devices: 发现的设备列表
            default_username: 默认IPMI用户名
            default_password: 默认IPMI密码
            group_id: 目标分组ID
        
        Returns:
            导入结果统计
        """
        logger.info(f"开始批量导入 {len(discovered_devices)} 台服务器")
        
        success_count = 0
        failed_count = 0
        failed_details = []
        
        for device in discovered_devices:
            try:
                # 检查IP是否已存在
                if self.server_service.get_server_by_ipmi_ip(device["ip"]):
                    failed_count += 1
                    failed_details.append({
                        "ip": device["ip"],
                        "error": "IPMI IP地址已存在"
                    })
                    continue
                
                # 生成服务器名称
                server_name = self._generate_server_name(device)
                
                # 检查名称是否已存在
                if self.server_service.get_server_by_name(server_name):
                    # 如果名称已存在，加上IP后缀
                    server_name = f"{server_name}-{device['ip'].replace('.', '-')}"
                
                # 使用设备发现的凭据或默认凭据
                username = device.get("username") or default_username
                password = device.get("password") or default_password
                
                # 创建服务器数据
                server_data = ServerCreate(
                    name=server_name,
                    ipmi_ip=device["ip"],
                    ipmi_username=username,
                    ipmi_password=password,
                    ipmi_port=device.get("port", 623),
                    manufacturer=device.get("manufacturer", ""),
                    model=device.get("model", ""),
                    serial_number=device.get("serial_number", ""),
                    description=f"通过设备发现功能自动导入",
                    group_id=group_id
                )
                
                # 创建服务器
                self.server_service.create_server(server_data)
                success_count += 1
                
                logger.info(f"成功导入服务器: {server_name} ({device['ip']})")
                
            except Exception as e:
                failed_count += 1
                failed_details.append({
                    "ip": device["ip"],
                    "error": str(e)
                })
                logger.error(f"导入服务器失败 {device['ip']}: {str(e)}")
        
        result = {
            "total_count": len(discovered_devices),
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_details": failed_details
        }
        
        logger.info(f"批量导入完成: 成功 {success_count}, 失败 {failed_count}")
        return result
    
    def _generate_server_name(self, device: Dict[str, Any]) -> str:
        """生成服务器名称"""
        manufacturer = device.get("manufacturer", "").strip()
        model = device.get("model", "").strip()
        ip = device["ip"]
        
        if manufacturer and model:
            # 清理制造商和型号中的特殊字符
            clean_manufacturer = "".join(c for c in manufacturer if c.isalnum())[:10]
            clean_model = "".join(c for c in model if c.isalnum())[:10]
            return f"{clean_manufacturer}-{clean_model}-{ip.replace('.', '-')}"
        elif manufacturer:
            clean_manufacturer = "".join(c for c in manufacturer if c.isalnum())[:15]
            return f"{clean_manufacturer}-{ip.replace('.', '-')}"
        else:
            return f"Server-{ip.replace('.', '-')}"
    
    def import_from_csv(self, csv_content: str, group_id: Optional[int] = None) -> Dict[str, Any]:
        """
        从CSV内容导入服务器
        
        CSV格式要求:
        name,ipmi_ip,ipmi_username,ipmi_password,ipmi_port,manufacturer,model,serial_number,description
        
        Args:
            csv_content: CSV文件内容
            group_id: 目标分组ID
        
        Returns:
            导入结果统计
        """
        logger.info("开始从CSV导入服务器")
        
        success_count = 0
        failed_count = 0
        failed_details = []
        
        try:
            # 解析CSV内容
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            # 验证CSV头部
            required_fields = {"name", "ipmi_ip", "ipmi_username", "ipmi_password"}
            if not required_fields.issubset(set(csv_reader.fieldnames or [])):
                raise ValidationError(f"CSV文件缺少必需字段: {required_fields}")
            
            # 逐行处理
            for row_num, row in enumerate(csv_reader, start=2):  # 从第2行开始计数（第1行是头部）
                try:
                    # 清理空白字符
                    cleaned_row = {k: v.strip() if v else "" for k, v in row.items()}
                    
                    # 验证必需字段
                    if not cleaned_row.get("name"):
                        raise ValidationError("服务器名称不能为空")
                    if not cleaned_row.get("ipmi_ip"):
                        raise ValidationError("IPMI IP地址不能为空")
                    if not cleaned_row.get("ipmi_username"):
                        raise ValidationError("IPMI用户名不能为空")
                    if not cleaned_row.get("ipmi_password"):
                        raise ValidationError("IPMI密码不能为空")
                    
                    # 验证IP格式
                    try:
                        ipaddress.IPv4Address(cleaned_row["ipmi_ip"])
                    except Exception:
                        raise ValidationError("IPMI IP地址格式无效")
                    
                    # 验证端口
                    ipmi_port = 623  # 默认端口
                    if cleaned_row.get("ipmi_port"):
                        try:
                            ipmi_port = int(cleaned_row["ipmi_port"])
                            if not (1 <= ipmi_port <= 65535):
                                raise ValidationError("IPMI端口必须在1-65535范围内")
                        except ValueError:
                            raise ValidationError("IPMI端口必须是数字")
                    
                    # 检查名称和IP唯一性
                    if self.server_service.get_server_by_name(cleaned_row["name"]):
                        raise ValidationError("服务器名称已存在")
                    if self.server_service.get_server_by_ipmi_ip(cleaned_row["ipmi_ip"]):
                        raise ValidationError("IPMI IP地址已存在")
                    
                    # 创建服务器数据
                    server_data = ServerCreate(
                        name=cleaned_row["name"],
                        ipmi_ip=cleaned_row["ipmi_ip"],
                        ipmi_username=cleaned_row["ipmi_username"],
                        ipmi_password=cleaned_row["ipmi_password"],
                        ipmi_port=ipmi_port,
                        manufacturer=cleaned_row.get("manufacturer", ""),
                        model=cleaned_row.get("model", ""),
                        serial_number=cleaned_row.get("serial_number", ""),
                        description=cleaned_row.get("description", "通过CSV文件导入"),
                        group_id=group_id
                    )
                    
                    # 创建服务器
                    self.server_service.create_server(server_data)
                    success_count += 1
                    
                    logger.info(f"成功导入服务器: {cleaned_row['name']} ({cleaned_row['ipmi_ip']})")
                    
                except Exception as e:
                    failed_count += 1
                    failed_details.append({
                        "row": row_num,
                        "name": row.get("name", ""),
                        "ipmi_ip": row.get("ipmi_ip", ""),
                        "error": str(e)
                    })
                    logger.error(f"CSV第{row_num}行导入失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"CSV解析失败: {str(e)}")
            raise ValidationError(f"CSV文件格式错误: {str(e)}")
        
        result = {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_details": failed_details
        }
        
        logger.info(f"CSV导入完成: 成功 {success_count}, 失败 {failed_count}")
        return result
    
    def generate_csv_template(self) -> str:
        """生成CSV导入模板"""
        template_rows = [
            ["name", "ipmi_ip", "ipmi_username", "ipmi_password", "ipmi_port", "manufacturer", "model", "serial_number", "description"],
            ["Server-001", "192.168.1.100", "admin", "password", "623", "Dell", "PowerEdge R740", "ABC123", "Production server"],
            ["Server-002", "192.168.1.101", "root", "calvin", "623", "HP", "ProLiant DL380", "DEF456", "Development server"]
        ]
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(template_rows)
        return output.getvalue()