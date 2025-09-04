from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class MonitoringRecord(Base):
    __tablename__ = "monitoring_records"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False, index=True)
    
    # 监控指标
    metric_type = Column(String(50), nullable=False, index=True)  # temperature, voltage, fan_speed等
    metric_name = Column(String(100), nullable=False)  # 具体传感器名称
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)  # 单位
    
    # 状态信息
    status = Column(String(20), nullable=True)  # ok, warning, critical
    threshold_min = Column(Float, nullable=True)
    threshold_max = Column(Float, nullable=True)
    
    # 原始数据
    raw_data = Column(Text, nullable=True)  # JSON格式存储原始IPMI数据
    
    # 时间戳
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # 关联服务器
    server = relationship("Server")