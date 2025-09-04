from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user import UserService
from app.services.auth import AuthService
from app.core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_admin_user)
):
    """创建用户（仅管理员）"""
    try:
        user_service = UserService(db)
        return user_service.create_user(user_data)
    except ValidationError as e:
        logger.warning(f"用户创建验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
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
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """更新用户信息"""
    try:
        user_service = UserService(db)
        user = user_service.update_user(user_id, user_data)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user
    except ValidationError as e:
        logger.warning(f"用户更新验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except HTTPException:
        raise  # 重新抛出HTTPException
    except Exception as e:
        logger.error(f"用户更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="用户更新失败，请稍后重试")

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_admin_user)
):
    """删除用户（仅管理员）"""
    user_service = UserService(db)
    success = user_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"message": "用户删除成功"}