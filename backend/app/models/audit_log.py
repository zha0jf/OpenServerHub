from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.sql import func
import enum

from app.core.database import Base

class AuditAction(str, enum.Enum):
    """审计操作类型"""
    # 用户认证相关
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    
    # 用户管理相关
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_ROLE_CHANGE = "user_role_change"
    
    # 服务器管理相关
    SERVER_CREATE = "server_create"
    SERVER_UPDATE = "server_update"
    SERVER_DELETE = "server_delete"
    SERVER_IMPORT = "server_import"
    
    # 电源控制相关
    POWER_ON = "power_on"
    POWER_OFF = "power_off"
    POWER_RESTART = "power_restart"
    POWER_FORCE_OFF = "power_force_off"
    POWER_FORCE_RESTART = "power_force_restart"
    
    # LED/定位灯控制
    LED_ON = "led_on"
    LED_OFF = "led_off"
    
    # 批量操作
    BATCH_POWER_CONTROL = "batch_power_control"
    BATCH_GROUP_CHANGE = "batch_group_change"
    
    # 监控相关
    MONITORING_ENABLE = "monitoring_enable"
    MONITORING_DISABLE = "monitoring_disable"
    
    # 服务器发现相关
    DISCOVERY_START = "discovery_start"
    DISCOVERY_COMPLETE = "discovery_complete"
    
    # 组管理相关
    GROUP_CREATE = "group_create"
    GROUP_UPDATE = "group_update"
    GROUP_DELETE = "group_delete"
    
    # 审计日志相关
    AUDIT_LOG_EXPORT = "audit_log_export"
    AUDIT_LOG_CLEANUP = "audit_log_cleanup"
    AUDIT_LOG_VIEW = "audit_log_view"
    
    # 数据库备份相关
    BACKUP_CREATE = "backup_create"
    BACKUP_DELETE = "backup_delete"
    BACKUP_RESTORE = "backup_restore"
    BACKUP_VERIFY = "backup_verify"
    BACKUP_DOWNLOAD = "backup_download"

class AuditResourceType(str, enum.Enum):
    """审计资源类型"""
    USER = "user"
    SERVER = "server"
    GROUP = "group"
    DISCOVERY = "discovery"
    AUDIT_LOG = "audit_log"
    MONITORING = "monitoring"
    BACKUP = "backup"

class AuditStatus(str, enum.Enum):
    """审计操作状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # 用于批量操作中的部分成功

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 操作信息
    action = Column(Enum(AuditAction), nullable=False, index=True)
    status = Column(Enum(AuditStatus), default=AuditStatus.SUCCESS, nullable=False)
    
    # 操作者信息
    operator_id = Column(Integer, nullable=True, index=True)  # 用户ID，某些操作可能没有操作者（如系统操作）
    operator_username = Column(String(50), nullable=True)  # 冗余存储用户名，防止用户删除后无法查询
    
    # 操作对象信息
    resource_type = Column(String(50), nullable=True, index=True)  # 如 "user", "server", "group"
    resource_id = Column(Integer, nullable=True, index=True)  # 如服务器ID、用户ID
    resource_name = Column(String(255), nullable=True)  # 如服务器名称、用户名
    
    # 操作内容和结果
    action_details = Column(Text, nullable=True)  # JSON格式，记录操作的详细参数
    result = Column(Text, nullable=True)  # JSON格式，记录操作结果
    error_message = Column(Text, nullable=True)  # 操作失败时的错误信息
    
    # 请求信息
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(String(255), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    def __repr__(self):
        return f"<AuditLog {self.id}: {self.action} by {self.operator_username} at {self.created_at}>"