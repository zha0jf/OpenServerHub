from app.core.database import Base

# 导入所有模型以确保它们被SQLAlchemy识别
from app.models.user import User, UserRole
from app.models.server import Server, ServerGroup
from app.models.monitoring import MonitoringRecord

__all__ = ["Base", "User", "UserRole", "Server", "ServerGroup", "MonitoringRecord"]