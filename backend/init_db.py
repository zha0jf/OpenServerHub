#!/usr/bin/env python3
"""
数据库初始化脚本
创建默认管理员用户和基础数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models import Base, User, UserRole
from app.services.user import UserService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """初始化数据库"""
    logger.info("开始初始化数据库...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")
    
    # 创建默认管理员用户
    db = SessionLocal()
    try:
        user_service = UserService(db)
        
        # 检查是否已存在管理员用户
        admin_user = user_service.get_user_by_username("admin")
        if not admin_user:
            from app.schemas.user import UserCreate
            admin_data = UserCreate(
                username="admin",
                email="admin@openshub.com",
                password="admin123",  # 生产环境请更改密码
                role=UserRole.ADMIN,
                is_active=True
            )
            
            admin_user = user_service.create_user(admin_data)
            logger.info(f"创建默认管理员用户: {admin_user.username}")
        else:
            logger.info("管理员用户已存在，跳过创建")
            
    except Exception as e:
        logger.error(f"创建默认用户失败: {e}")
        db.rollback()
    finally:
        db.close()
    
    logger.info("数据库初始化完成")

if __name__ == "__main__":
    init_database()