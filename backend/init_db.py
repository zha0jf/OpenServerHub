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
from app.models import Base, User, UserRole, Server, ServerGroup
from app.services.user import UserService
from app.services.server import ServerService
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
        server_service = ServerService(db)
        
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
            
        # 创建测试服务器分组
        test_group = server_service.get_server_group_by_name("测试环境")
        if not test_group:
            from app.schemas.server import ServerGroupCreate
            group_data = ServerGroupCreate(
                name="测试环境",
                description="用于测试的服务器分组"
            )
            test_group = server_service.create_server_group(group_data)
            logger.info(f"创建测试服务器分组: {test_group.name}")
        else:
            logger.info("测试服务器分组已存在，跳过创建")
            
        # 创建测试服务器数据（注意：已移除hostname字段）
        test_server = server_service.get_server_by_name("测试服务器01")
        if not test_server:
            from app.schemas.server import ServerCreate
            server_data = ServerCreate(
                name="测试服务器01",
                ipmi_ip="192.168.1.100",
                ipmi_username="admin",
                ipmi_password="admin123",
                ipmi_port=623,
                manufacturer="Dell",
                model="PowerEdge R740",
                serial_number="TEST001",
                description="用于测试的服务器实例",
                tags="test,demo",
                group_id=test_group.id
            )
            test_server = server_service.create_server(server_data)
            logger.info(f"创建测试服务器: {test_server.name}")
        else:
            logger.info("测试服务器已存在，跳过创建")
            
    except Exception as e:
        logger.error(f"创建默认用户失败: {e}")
        db.rollback()
    finally:
        db.close()
    
    logger.info("数据库初始化完成")

if __name__ == "__main__":
    init_database()