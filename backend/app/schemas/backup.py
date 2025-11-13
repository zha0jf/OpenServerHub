from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BackupCreate(BaseModel):
    """创建备份请求"""
    pass

class BackupResponse(BaseModel):
    """备份文件信息响应"""
    filename: str
    size: int
    created_at: datetime
    file_path: str

class BackupListResponse(BaseModel):
    """备份文件列表响应"""
    backups: List[BackupResponse]

class BackupDeleteRequest(BaseModel):
    """删除备份请求"""
    filename: str

class BackupRestoreRequest(BaseModel):
    """恢复备份请求"""
    filename: str

class BackupVerifyResponse(BaseModel):
    """备份验证响应"""
    filename: str
    is_valid: bool
    message: str