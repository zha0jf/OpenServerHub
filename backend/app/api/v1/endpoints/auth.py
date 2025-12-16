from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.config import settings
from app.schemas.auth import Token, UserLogin
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.services.audit_log import AuditLogService
from app.models.audit_log import AuditAction, AuditStatus

router = APIRouter()

def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    # 检查X-Forwarded-For头（用于代理/负载均衡器）
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    # 检查X-Real-IP头
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"]
    # 使用直接连接IP
    return request.client.host if request.client else "unknown"

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: AsyncSession = Depends(get_async_db)
):
    """用户登录"""
    auth_service = AuthService(db)
    audit_service = AuditLogService(db)
    
    # 获取客户端信息
    client_ip = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"
    
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        # 记录失败的登录尝试
        await audit_service.log_login(
            username=form_data.username,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 记录成功的登录
    await audit_service.log_login(
        username=user.username,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        success=True,
    )
    
    access_token = auth_service.create_access_token(user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@router.post("/logout")
async def logout(
    request: Request = None,
    current_user = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """用户登出"""
    audit_service = AuditLogService(db)
    
    # 获取客户端信息
    client_ip = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"
    
    # 记录登出操作
    await audit_service.log_logout(
        user_id=current_user.id,
        username=current_user.username,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    
    return {"message": "成功登出"}

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user = Depends(AuthService.get_current_user)
):
    """获取当前用户信息"""
    return UserResponse.model_validate(current_user)