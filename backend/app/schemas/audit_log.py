from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, Union

class AuditLogBase(BaseModel):
    action: str
    status: str
    operator_id: Optional[int] = None
    operator_username: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    action_details: Optional[Union[Dict[str, Any], str]] = None
    result: Optional[Union[Dict[str, Any], str]] = None
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class AuditLogListResponse(BaseModel):
    """审计日志列表响应"""
    items: list[AuditLog]
    total: int
    skip: int
    limit: int
    
    class Config:
        from_attributes = True
