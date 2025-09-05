from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.server import ServerStatus, PowerState
import re

class ServerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="服务器名称")
    ipmi_ip: str = Field(..., description="IPMI IP地址")
    ipmi_username: str = Field(..., min_length=1, max_length=50, description="IPMI用户名")
    ipmi_port: int = Field(default=623, ge=1, le=65535, description="IPMI端口号")
    manufacturer: Optional[str] = Field(None, max_length=100, description="厂商")
    model: Optional[str] = Field(None, max_length=100, description="型号")
    serial_number: Optional[str] = Field(None, max_length=100, description="序列号")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    tags: Optional[str] = Field(None, max_length=200, description="标签")
    group_id: Optional[int] = Field(None, description="分组ID")
    
    @validator('ipmi_ip')
    def validate_ipmi_ip(cls, v):
        # IP地址格式验证
        ip_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if not re.match(ip_pattern, v):
            raise ValueError('请输入有效的IP地址')
        return v

class ServerCreate(ServerBase):
    ipmi_password: str = Field(..., min_length=1, max_length=128, description="IPMI密码")

class ServerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    ipmi_ip: Optional[str] = None
    ipmi_username: Optional[str] = Field(None, min_length=1, max_length=50)
    ipmi_password: Optional[str] = Field(None, min_length=1, max_length=128)
    ipmi_port: Optional[int] = Field(None, ge=1, le=65535)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[str] = Field(None, max_length=200)
    group_id: Optional[int] = None
    
    @validator('ipmi_ip')
    def validate_ipmi_ip(cls, v):
        if v is not None:
            ip_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            if not re.match(ip_pattern, v):
                raise ValueError('请输入有效的IP地址')
        return v

class ServerResponse(ServerBase):
    id: int
    status: ServerStatus
    power_state: PowerState
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ServerGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="分组名称")
    description: Optional[str] = Field(None, max_length=500, description="分组描述")

class ServerGroupCreate(ServerGroupBase):
    pass

class ServerGroupResponse(ServerGroupBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# 批量操作相关模式
class BatchPowerRequest(BaseModel):
    """批量电源操作请求"""
    server_ids: List[int] = Field(..., min_items=1, max_items=50, description="服务器ID列表")
    action: str = Field(..., description="电源操作类型: on, off, restart, force_off")
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['on', 'off', 'restart', 'force_off']
        if v not in allowed_actions:
            raise ValueError(f'不支持的操作类型，支持的操作: {", ".join(allowed_actions)}')
        return v

class BatchOperationResult(BaseModel):
    """批量操作结果"""
    server_id: int
    server_name: str
    success: bool
    message: str
    error: Optional[str] = None

class BatchPowerResponse(BaseModel):
    """批量电源操作响应"""
    total_count: int = Field(description="总服务器数量")
    success_count: int = Field(description="成功操作数量")
    failed_count: int = Field(description="失败操作数量")
    results: List[BatchOperationResult] = Field(description="详细操作结果")
    
class ClusterStatsResponse(BaseModel):
    """集群统计信息响应"""
    total_servers: int = Field(description="服务器总数")
    online_servers: int = Field(description="在线服务器数")
    offline_servers: int = Field(description="离线服务器数")
    unknown_servers: int = Field(description="状态未知服务器数")
    power_on_servers: int = Field(description="开机服务器数")
    power_off_servers: int = Field(description="关机服务器数")
    group_stats: Dict[str, Any] = Field(description="分组统计信息")
    manufacturer_stats: Dict[str, int] = Field(description="厂商分布统计")

# 设备发现相关Schema
class NetworkScanRequest(BaseModel):
    """网络扫描请求"""
    network: str = Field(..., description="网络范围，支持CIDR格式或IP范围格式")
    port: int = Field(default=623, ge=1, le=65535, description="扫描端口")
    timeout: int = Field(default=3, ge=1, le=30, description="超时时间（秒）")
    max_workers: int = Field(default=50, ge=1, le=100, description="最大并发数")
    
    @validator('network')
    def validate_network(cls, v):
        """验证网络格式"""
        # 简单的格式验证，具体解析逻辑在服务层
        if not v or len(v.strip()) == 0:
            raise ValueError('网络范围不能为空')
        return v.strip()

class DiscoveredDevice(BaseModel):
    """发现的设备信息"""
    ip: str = Field(description="设备IP地址")
    port: int = Field(description="IPMI端口")
    username: str = Field(description="可用的用户名")
    password: str = Field(description="可用的密码")
    manufacturer: str = Field(description="制造商")
    model: str = Field(description="型号")
    serial_number: str = Field(description="序列号")
    bmc_version: str = Field(description="BMC版本")
    accessible: bool = Field(description="是否可访问")
    auth_required: bool = Field(description="是否需要认证")
    already_exists: bool = Field(default=False, description="是否已存在于系统中")
    existing_server_id: Optional[int] = Field(default=None, description="已存在的服务器ID")
    existing_server_name: Optional[str] = Field(default=None, description="已存在的服务器名称")

class NetworkScanResponse(BaseModel):
    """网络扫描响应"""
    total_scanned: int = Field(description="扫描的IP总数")
    devices_found: int = Field(description="发现的设备数量")
    devices: List[DiscoveredDevice] = Field(description="发现的设备列表")
    scan_duration: float = Field(description="扫描耗时（秒）")

class BatchImportRequest(BaseModel):
    """批量导入请求"""
    devices: List[Dict[str, Any]] = Field(..., min_items=1, description="要导入的设备列表")
    default_username: str = Field(default="", description="默认IPMI用户名")
    default_password: str = Field(default="", description="默认IPMI密码")
    group_id: Optional[int] = Field(None, description="目标分组ID")

class BatchImportResponse(BaseModel):
    """批量导入响应"""
    total_count: int = Field(description="总导入数量")
    success_count: int = Field(description="成功导入数量")
    failed_count: int = Field(description="失败导入数量")
    failed_details: List[Dict[str, Any]] = Field(description="失败详情")

class CSVImportRequest(BaseModel):
    """CSV导入请求"""
    csv_content: str = Field(..., description="CSV文件内容")
    group_id: Optional[int] = Field(None, description="目标分组ID")

class CSVImportResponse(BaseModel):
    """CSV导入响应"""
    success_count: int = Field(description="成功导入数量")
    failed_count: int = Field(description="失败导入数量")
    failed_details: List[Dict[str, Any]] = Field(description="失败详情")