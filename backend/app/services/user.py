from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import ValidationError
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        # bcrypt对密码长度有限制，不能超过72字节
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            raise ValidationError("密码不能超过72个字节，请缩短密码长度")
        return pwd_context.hash(password)

    def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        # 检查用户名是否已存在
        if self.get_user_by_username(user_data.username):
            raise ValidationError("用户名已存在")
        
        # 检查邮箱是否已存在
        if self.get_user_by_email(user_data.email):
            raise ValidationError("邮箱已存在")
        
        # 创建用户
        try:
            password_hash = self.get_password_hash(user_data.password)
        except Exception as e:
            raise ValidationError(f"密码哈希处理失败: {str(e)}")
        
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role,
            is_active=user_data.is_active
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_user(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(User.email == email).first()

    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """获取用户列表"""
        return self.db.query(User).offset(skip).limit(limit).all()

    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """更新用户信息"""
        db_user = self.get_user(user_id)
        if not db_user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        
        # 处理密码更新
        if "password" in update_data:
            try:
                update_data["password_hash"] = self.get_password_hash(update_data.pop("password"))
            except Exception as e:
                raise ValidationError(f"密码哈希处理失败: {str(e)}")
        
        # 检查用户名和邮箱唯一性
        if "username" in update_data and update_data["username"] != db_user.username:
            if self.get_user_by_username(update_data["username"]):
                raise ValidationError("用户名已存在")
        
        if "email" in update_data and update_data["email"] != db_user.email:
            if self.get_user_by_email(update_data["email"]):
                raise ValidationError("邮箱已存在")
        
        # 更新用户信息
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        db_user = self.get_user(user_id)
        if not db_user:
            return False
        
        self.db.delete(db_user)
        self.db.commit()
        return True