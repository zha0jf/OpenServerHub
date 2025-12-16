from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole
import re

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名，3-50个字符")
    email: str = Field(..., description="电子邮箱地址")
    role: UserRole = Field(default=UserRole.USER, description="用户角色")
    is_active: bool = Field(default=True, description="是否激活")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('用户名只能包含字母、数字、下划线和短横线')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        # 基本的邮箱格式验证，允许测试邮箱
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('请输入有效的邮箱地址')
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128, description="密码，至少6个字符")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少6个字符')
        return v

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is not None:
            # 基本的邮箱格式验证，允许测试邮箱
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('请输入有效的邮箱地址')
        return v

class UserResponse(UserBase):
    id: int
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True