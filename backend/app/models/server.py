from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base

class ServerStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    ERROR = "error"

class PowerState(str, enum.Enum):
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"

class Server(Base):
    __tablename__ = "servers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    ipmi_ip = Column(String(15), nullable=False, index=True)
    ipmi_username = Column(String(50), nullable=False)
    ipmi_password = Column(String(255), nullable=False)
    ipmi_port = Column(Integer, default=623, nullable=False)
    
    # 监控启用状态
    monitoring_enabled = Column(Boolean, default=False, nullable=False)
    
    # 服务器信息
    manufacturer = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    
    # 状态信息
    status = Column(Enum(ServerStatus), default=ServerStatus.UNKNOWN, nullable=False)
    power_state = Column(Enum(PowerState), default=PowerState.UNKNOWN, nullable=False)
    last_seen = Column(DateTime, nullable=True)
    
    # 分组
    group_id = Column(Integer, ForeignKey("server_groups.id"), nullable=True)
    group = relationship("ServerGroup", back_populates="servers")
    
    # 备注和标签
    description = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)  # JSON格式存储标签
    
    # 时间戳
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class ServerGroup(Base):
    __tablename__ = "server_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # 关联服务器
    servers = relationship("Server", back_populates="group")
    
    # 时间戳
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)