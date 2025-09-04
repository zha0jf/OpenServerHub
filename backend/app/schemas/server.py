from pydantic import BaseModel, Field, validator
from typing import Optional, List
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