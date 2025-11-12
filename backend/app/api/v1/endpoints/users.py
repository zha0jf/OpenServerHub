from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user import UserService
from app.services.auth import AuthService
from app.services.audit_log import AuditLogService
from app.models.audit_log import AuditAction
from app.core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_admin_user)
):
    """创建用户（仅管理员）"""
    try:
        user_service = UserService(db)
        audit_service = AuditLogService(db)
        user = user_service.create_user(user_data)
        
        # 记录成功的用户创建操作
        audit_service.log_user_operation(
            operator_id=current_user.id,
            operator_username=current_user.username,
            action=AuditAction.USER_CREATE,
            target_user_id=user.id,
            target_username=user.username,
            action_details={"email": user.email, "role": str(user.role)},
            result={"status": "success", "user_id": user.id},
            success=True,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
        )
        
        return user
    except ValidationError as e:
        # 记录失败的用户创建操作
        try:
            audit_service_local = AuditLogService(db)
            audit_service_local.log_user_operation(
                operator_id=current_user.id,
                operator_username=current_user.username,
                action=AuditAction.USER_CREATE,
                target_username=user_data.username,
                success=False,
                error_message=e.message,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
            )
        except Exception as audit_error:
            logger.warning(f"记录用户创建失败操作失败: {str(audit_error)}")
        
        logger.warning(f"用户创建验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        # 记录失败的用户创建操作
        try:
            audit_service_local = AuditLogService(db)
            audit_service_local.log_user_operation(
                operator_id=current_user.id,
                operator_username=current_user.username,
                action=AuditAction.USER_CREATE,
                target_username=user_data.username,
                success=False,
                error_message=str(e),
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
            )
        except Exception as audit_error:
            logger.warning(f"记录用户创建失败操作失败: {str(audit_error)}")
        
        logger.error(f"用户创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail="用户创建失败，请稍后重试")

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取用户列表"""
    user_service = UserService(db)
    return user_service.get_users(skip=skip, limit=limit)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取指定用户"""
    user_service = UserService(db)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """更新用户信息"""
    try:
        user_service = UserService(db)
        audit_service = AuditLogService(db)
        user = user_service.update_user(user_id, user_data)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 记录成功的用户更新操作
        audit_service.log_user_operation(
            operator_id=current_user.id,
            operator_username=current_user.username,
            action=AuditAction.USER_UPDATE,
            target_user_id=user.id,
            target_username=user.username,
            action_details=user_data.model_dump(exclude_unset=True),
            result={"status": "success", "user_id": user.id},
            success=True,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
        )
        
        return user
    except ValidationError as e:
        # 记录失败的用户更新操作
        try:
            audit_service_local = AuditLogService(db)
            audit_service_local.log_user_operation(
                operator_id=current_user.id,
                operator_username=current_user.username,
                action=AuditAction.USER_UPDATE,
                target_user_id=user_id,
                success=False,
                error_message=e.message,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
            )
        except Exception as audit_error:
            logger.warning(f"记录用户更新失败操作失败: {str(audit_error)}")
        
        logger.warning(f"用户更新验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        # 记录失败的用户更新操作
        try:
            audit_service_local = AuditLogService(db)
            audit_service_local.log_user_operation(
                operator_id=current_user.id,
                operator_username=current_user.username,
                action=AuditAction.USER_UPDATE,
                target_user_id=user_id,
                success=False,
                error_message=str(e),
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
            )
        except Exception as audit_error:
            logger.warning(f"记录用户更新失败操作失败: {str(audit_error)}")
        
        logger.error(f"用户更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="用户更新失败，请稍后重试")

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_admin_user)
):
    """删除用户（仅管理员）"""
    try:
        user_service = UserService(db)
        audit_service = AuditLogService(db)
        
        # 获取用户信息用于审计日志
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        user_username = user.username
        success = user_service.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 记录成功的用户删除操作
        audit_service.log_user_operation(
            operator_id=current_user.id,
            operator_username=current_user.username,
            action=AuditAction.USER_DELETE,
            target_user_id=user_id,
            target_username=user_username,
            result={"status": "success", "deleted_user_id": user_id},
            success=True,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
        )
        
        return {"message": "用户删除成功"}
    except HTTPException:
        # 记录失败的用户删除操作
        try:
            audit_service_local = AuditLogService(db)
            audit_service_local.log_user_operation(
                operator_id=current_user.id,
                operator_username=current_user.username,
                action=AuditAction.USER_DELETE,
                target_user_id=user_id,
                success=False,
                error_message="用户不存在",
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
            )
        except Exception as audit_error:
            logger.warning(f"记录用户删除失败操作失败: {str(audit_error)}")
        raise
    except Exception as e:
        # 记录失败的用户删除操作
        try:
            audit_service_local = AuditLogService(db)
            audit_service_local.log_user_operation(
                operator_id=current_user.id,
                operator_username=current_user.username,
                action=AuditAction.USER_DELETE,
                target_user_id=user_id,
                success=False,
                error_message=str(e),
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
            )
        except Exception as audit_error:
            logger.warning(f"记录用户删除失败操作失败: {str(audit_error)}")
        
        logger.error(f"用户删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail="用户删除失败，请稍后重试")