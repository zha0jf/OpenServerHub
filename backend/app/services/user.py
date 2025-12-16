import asyncio
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import ValidationError
from app.core import security

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _hash_password(self, password: str) -> str:
        """内部辅助：异步执行密码哈希"""
        loop = asyncio.get_running_loop()
        # 调用 security 模块的同步函数
        return await loop.run_in_executor(None, security.get_password_hash, password)

    async def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        # 检查用户名是否已存在
        if await self.get_user_by_username(user_data.username):
            raise ValidationError("用户名已存在")
        
        # 检查邮箱是否已存在
        if await self.get_user_by_email(user_data.email):
            raise ValidationError("邮箱已存在")
        
        # 创建用户
        try:
            password_hash = await self._hash_password(user_data.password)
        except Exception as e:
            raise ValidationError(f"密码处理失败: {str(e)}")
        
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role,
            is_active=user_data.is_active
        )
        
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user

    async def get_user(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """获取用户列表"""
        stmt = select(User).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """更新用户信息"""
        db_user = await self.get_user(user_id)
        if not db_user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        
        # 处理密码更新
        if "password" in update_data:
            try:
                update_data["password_hash"] = await self._hash_password(update_data.pop("password"))
            except Exception as e:
                raise ValidationError(f"密码处理失败: {str(e)}")
        
        # 检查用户名和邮箱唯一性
        if "username" in update_data and update_data["username"] != db_user.username:
            if await self.get_user_by_username(update_data["username"]):
                raise ValidationError("用户名已存在")
        
        if "email" in update_data and update_data["email"] != db_user.email:
            if await self.get_user_by_email(update_data["email"]):
                raise ValidationError("邮箱已存在")
        
        # 更新用户信息
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user

    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        db_user = await self.get_user(user_id)
        if not db_user:
            return False
        
        await self.db.delete(db_user)
        await self.db.commit()
        return True