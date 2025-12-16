from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_async_db
from app.schemas.backup import (
    BackupCreate, BackupResponse, BackupListResponse, 
    BackupDeleteRequest, BackupRestoreRequest, BackupVerifyResponse
)
from app.services.backup import BackupService
from app.services.auth import get_current_admin_user
from app.services.audit_log import AuditLogService
from app.models.audit_log import AuditAction, AuditResourceType, AuditStatus

router = APIRouter()
logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"]
    return request.client.host if request.client else "unknown"

@router.post("/create", response_model=BackupResponse)
async def create_backup(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_admin_user)
):
    """创建数据库备份（仅管理员）"""
    logger.debug(f"用户 {current_user.username} 请求创建数据库备份")
    audit_service = AuditLogService(db)
    
    try:
        backup_service = BackupService()
        filename = backup_service.create_backup()
        
        # 获取备份文件信息
        backups = backup_service.list_backups()
        backup_info = next((b for b in backups if b["filename"] == filename), None)
        
        if backup_info:
            # 记录审计日志
            await audit_service.create_log(
                action=AuditAction.BACKUP_CREATE,
                operator_id=current_user.id,
                operator_username=current_user.username,
                resource_type=AuditResourceType.BACKUP,
                resource_name=filename,
                action_details={"filename": filename},
                result={
                    "filename": backup_info["filename"],
                    "size": backup_info["size"],
                    "file_path": backup_info["file_path"]
                },
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("user-agent", "unknown"),
                status=AuditStatus.SUCCESS
            )
            
            logger.info(f"用户 {current_user.username} 成功创建数据库备份: {filename}")
            return BackupResponse(**backup_info)
        else:
            # 记录审计日志（失败）
            await audit_service.create_log(
                action=AuditAction.BACKUP_CREATE,
                operator_id=current_user.id,
                operator_username=current_user.username,
                resource_type=AuditResourceType.BACKUP,
                error_message="备份创建失败",
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("user-agent", "unknown"),
                status=AuditStatus.FAILED
            )
            
            raise HTTPException(status_code=500, detail="备份创建失败")
    except Exception as e:
        logger.error(f"创建数据库备份失败: {e}")
        
        # 记录审计日志（失败）
        await audit_service.create_log(
            action=AuditAction.BACKUP_CREATE,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type=AuditResourceType.BACKUP,
            error_message=str(e),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
            status=AuditStatus.FAILED
        )
        
        raise HTTPException(status_code=500, detail=f"创建数据库备份失败: {str(e)}")

@router.get("/list", response_model=BackupListResponse)
async def list_backups(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_admin_user)
):
    """列出所有备份文件（仅管理员）"""
    logger.debug(f"用户 {current_user.username} 请求列出备份文件")
    
    try:
        backup_service = BackupService()
        backups = backup_service.list_backups()
        
        logger.info(f"用户 {current_user.username} 成功列出 {len(backups)} 个备份文件")
        return BackupListResponse(backups=[BackupResponse(**backup) for backup in backups])
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取备份列表失败: {str(e)}")

@router.delete("/delete", response_model=bool)
async def delete_backup(
    request: Request,
    delete_request: BackupDeleteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_admin_user)
):
    """删除备份文件（仅管理员）"""
    logger.debug(f"用户 {current_user.username} 请求删除备份文件: {delete_request.filename}")
    audit_service = AuditLogService(db)
    
    try:
        backup_service = BackupService()
        result = backup_service.delete_backup(delete_request.filename)
        
        # 记录审计日志
        await audit_service.create_log(
            action=AuditAction.BACKUP_DELETE,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type=AuditResourceType.BACKUP,
            resource_name=delete_request.filename,
            action_details={"filename": delete_request.filename},
            result={"success": result},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
            status=AuditStatus.SUCCESS if result else AuditStatus.FAILED
        )
        
        logger.info(f"用户 {current_user.username} 删除备份文件 {'成功' if result else '失败'}: {delete_request.filename}")
        return result
    except Exception as e:
        logger.error(f"删除备份文件失败: {e}")
        
        # 记录审计日志（失败）
        await audit_service.create_log(
            action=AuditAction.BACKUP_DELETE,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type=AuditResourceType.BACKUP,
            resource_name=delete_request.filename,
            action_details={"filename": delete_request.filename},
            error_message=str(e),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
            status=AuditStatus.FAILED
        )
        
        raise HTTPException(status_code=500, detail=f"删除备份文件失败: {str(e)}")

@router.post("/restore", response_model=bool)
async def restore_backup(
    request: Request,
    restore_request: BackupRestoreRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_admin_user)
):
    """恢复数据库备份（仅管理员）"""
    logger.debug(f"用户 {current_user.username} 请求恢复数据库备份: {restore_request.filename}")
    audit_service = AuditLogService(db)
    
    try:
        backup_service = BackupService()
        result = backup_service.restore_backup(restore_request.filename)
        
        # 记录审计日志
        await audit_service.create_log(
            action=AuditAction.BACKUP_RESTORE,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type=AuditResourceType.BACKUP,
            resource_name=restore_request.filename,
            action_details={"filename": restore_request.filename},
            result={"success": result},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
            status=AuditStatus.SUCCESS if result else AuditStatus.FAILED
        )
        
        logger.info(f"用户 {current_user.username} 恢复数据库备份 {'成功' if result else '失败'}: {restore_request.filename}")
        return result
    except Exception as e:
        logger.error(f"恢复数据库备份失败: {e}")
        
        # 记录审计日志（失败）
        await audit_service.create_log(
            action=AuditAction.BACKUP_RESTORE,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type=AuditResourceType.BACKUP,
            resource_name=restore_request.filename,
            action_details={"filename": restore_request.filename},
            error_message=str(e),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
            status=AuditStatus.FAILED
        )
        
        raise HTTPException(status_code=500, detail=f"恢复数据库备份失败: {str(e)}")

@router.post("/verify", response_model=BackupVerifyResponse)
async def verify_backup(
    request: Request,
    verify_request: BackupRestoreRequest,  # 重用RestoreRequest，因为只需要filename
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_admin_user)
):
    """验证备份文件完整性（仅管理员）"""
    logger.debug(f"用户 {current_user.username} 请求验证备份文件完整性: {verify_request.filename}")
    audit_service = AuditLogService(db)
    
    try:
        backup_service = BackupService()
        result = backup_service.verify_backup(verify_request.filename)
        
        # 记录审计日志
        await audit_service.create_log(
            action=AuditAction.BACKUP_VERIFY,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type=AuditResourceType.BACKUP,
            resource_name=verify_request.filename,
            action_details={"filename": verify_request.filename},
            result=result,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
            status=AuditStatus.SUCCESS
        )
        
        logger.info(f"用户 {current_user.username} 验证备份文件完成: {verify_request.filename}, 结果: {result['message']}")
        return BackupVerifyResponse(**result)
    except Exception as e:
        logger.error(f"验证备份文件失败: {e}")
        
        # 记录审计日志（失败）
        await audit_service.create_log(
            action=AuditAction.BACKUP_VERIFY,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type=AuditResourceType.BACKUP,
            resource_name=verify_request.filename,
            action_details={"filename": verify_request.filename},
            error_message=str(e),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
            status=AuditStatus.FAILED
        )
        
        raise HTTPException(status_code=500, detail=f"验证备份文件失败: {str(e)}")

@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_admin_user)
):
    """下载备份文件（仅管理员）"""
    logger.debug(f"用户 {current_user.username} 请求下载备份文件: {filename}")
    audit_service = AuditLogService(db)
    
    try:
        backup_service = BackupService()
        backup_path = backup_service.backup_dir / filename
        
        # 检查文件是否存在
        if not backup_path.exists() or not backup_path.is_file():
            logger.error(f"备份文件不存在: {filename}")
            raise HTTPException(status_code=404, detail="备份文件不存在")
        
        # 记录审计日志
        await audit_service.create_log(
            action=AuditAction.BACKUP_DOWNLOAD,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type=AuditResourceType.BACKUP,
            resource_name=filename,
            action_details={"filename": filename},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
            status=AuditStatus.SUCCESS
        )
        
        logger.info(f"用户 {current_user.username} 下载备份文件: {filename}")
        return FileResponse(
            path=str(backup_path),
            filename=filename,
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载备份文件失败: {e}")
        
        # 记录审计日志（失败）
        await audit_service.create_log(
            action=AuditAction.BACKUP_DOWNLOAD,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type=AuditResourceType.BACKUP,
            resource_name=filename,
            action_details={"filename": filename},
            error_message=str(e),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent", "unknown"),
            status=AuditStatus.FAILED
        )
        
        raise HTTPException(status_code=500, detail=f"下载备份文件失败: {str(e)}")