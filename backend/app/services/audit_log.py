import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog, AuditAction, AuditStatus

logger = logging.getLogger(__name__)

class AuditLogService:
    """审计日志服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_log(
        self,
        action: AuditAction,
        operator_id: Optional[int] = None,
        operator_username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        resource_name: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: AuditStatus = AuditStatus.SUCCESS,
    ) -> AuditLog:
        """
        创建审计日志
        
        :param action: 操作类型
        :param operator_id: 操作者ID
        :param operator_username: 操作者用户名
        :param resource_type: 资源类型 (user, server, group等)
        :param resource_id: 资源ID
        :param resource_name: 资源名称
        :param action_details: 操作详情（JSON）
        :param result: 操作结果（JSON）
        :param error_message: 错误信息
        :param ip_address: IP地址
        :param user_agent: User Agent
        :param status: 操作状态
        :return: 创建的审计日志对象
        """
        
        audit_log = AuditLog(
            action=action,
            status=status,
            operator_id=operator_id,
            operator_username=operator_username,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            action_details=json.dumps(action_details) if action_details else None,
            result=json.dumps(result) if result else None,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        try:
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            logger.info(
                f"审计日志已记录: action={action}, operator={operator_username}, "
                f"resource={resource_type}:{resource_id}, status={status}"
            )
            return audit_log
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建审计日志失败: {str(e)}", exc_info=True)
            raise
    
    def get_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        action: Optional[AuditAction] = None,
        operator_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple[list[AuditLog], int]:
        """
        查询审计日志
        
        :param skip: 跳过记录数
        :param limit: 返回记录数
        :param action: 操作类型过滤
        :param operator_id: 操作者ID过滤
        :param resource_type: 资源类型过滤
        :param resource_id: 资源ID过滤
        :param start_date: 开始日期过滤
        :param end_date: 结束日期过滤
        :return: (日志列表, 总数)
        """
        
        query = self.db.query(AuditLog)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        if operator_id:
            query = query.filter(AuditLog.operator_id == operator_id)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        total = query.count()
        
        logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
        
        return logs, total
    
    def get_log_by_id(self, log_id: int) -> Optional[AuditLog]:
        """获取指定ID的审计日志"""
        return self.db.query(AuditLog).filter(AuditLog.id == log_id).first()
    
    def log_login(
        self,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[int] = None,
        success: bool = True,
    ) -> AuditLog:
        """记录登录操作"""
        return self.create_log(
            action=AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED,
            operator_id=user_id,
            operator_username=username,
            resource_type="user",
            resource_id=user_id,
            resource_name=username,
            ip_address=ip_address,
            user_agent=user_agent,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILED,
        )
    
    def log_logout(
        self,
        user_id: int,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录登出操作"""
        return self.create_log(
            action=AuditAction.LOGOUT,
            operator_id=user_id,
            operator_username=username,
            resource_type="user",
            resource_id=user_id,
            resource_name=username,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    def log_power_control(
        self,
        user_id: int,
        username: str,
        server_id: int,
        server_name: str,
        action_type: str,  # power_on, power_off, power_restart, power_force_off, power_force_restart
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录电源控制操作"""
        
        action_map = {
            "on": AuditAction.POWER_ON,
            "off": AuditAction.POWER_OFF,
            "restart": AuditAction.POWER_RESTART,
            "force_off": AuditAction.POWER_FORCE_OFF,
            "force_restart": AuditAction.POWER_FORCE_RESTART,
        }
        
        audit_action = action_map.get(action_type, AuditAction.POWER_ON)
        
        return self.create_log(
            action=audit_action,
            operator_id=user_id,
            operator_username=username,
            resource_type="server",
            resource_id=server_id,
            resource_name=server_name,
            action_details={"action_type": action_type},
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILED,
        )
    
    def log_server_operation(
        self,
        user_id: int,
        username: str,
        action: AuditAction,
        server_id: Optional[int] = None,
        server_name: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录服务器相关操作"""
        return self.create_log(
            action=action,
            operator_id=user_id,
            operator_username=username,
            resource_type="server",
            resource_id=server_id,
            resource_name=server_name,
            action_details=action_details,
            result=result,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILED,
        )
    
    def log_user_operation(
        self,
        operator_id: int,
        operator_username: str,
        action: AuditAction,
        target_user_id: Optional[int] = None,
        target_username: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录用户管理相关操作"""
        return self.create_log(
            action=action,
            operator_id=operator_id,
            operator_username=operator_username,
            resource_type="user",
            resource_id=target_user_id,
            resource_name=target_username,
            action_details=action_details,
            result=result,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILED,
        )
    
    def log_group_operation(
        self,
        user_id: int,
        username: str,
        action: AuditAction,
        group_id: Optional[int] = None,
        group_name: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录服务器分组相关操作"""
        return self.create_log(
            action=action,
            operator_id=user_id,
            operator_username=username,
            resource_type="group",
            resource_id=group_id,
            resource_name=group_name,
            action_details=action_details,
            result=result,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILED,
        )
    
    def log_batch_operation(
        self,
        user_id: int,
        username: str,
        action: AuditAction,
        action_details: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录批量操作相关审计日志"""
        return self.create_log(
            action=action,
            operator_id=user_id,
            operator_username=username,
            resource_type="batch",
            action_details=action_details,
            result=result,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILED,
        )
    
    def log_discovery_operation(
        self,
        user_id: int,
        username: str,
        action: AuditAction,
        action_details: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录设备发现相关操作"""
        return self.create_log(
            action=action,
            operator_id=user_id,
            operator_username=username,
            resource_type="discovery",
            action_details=action_details,
            result=result,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            status=AuditStatus.SUCCESS if success else AuditStatus.FAILED,
        )