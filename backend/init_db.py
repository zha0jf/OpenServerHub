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

# 导入Alembic相关模块
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """运行数据库迁移"""
    logger.info("开始运行数据库迁移...")
    
    try:
        # 配置Alembic
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("script_location", "alembic")
        
        # 连接数据库并获取当前版本
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            
        logger.info(f"当前数据库版本: {current_rev}")
        
        # 运行迁移到最新版本
        command.upgrade(alembic_cfg, "head")
        logger.info("数据库迁移完成")
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise

def init_database():
    """初始化数据库"""
    logger.info("开始初始化数据库...")
    
    # 首先运行迁移
    run_migrations()
    
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
                password="admin123",  # 生产环境请更改密码 (密码长度已控制在72字节以内)
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
            # 获取分组ID的实际值
            group_id_value = None
            if test_group:
                # 重新查询分组以获取实际的ID值
                actual_group = db.query(ServerGroup).filter(ServerGroup.name == "测试环境").first()
                if actual_group:
                    group_id_value = getattr(actual_group, 'id')  # 使用getattr获取实际值
            
            server_data = ServerCreate(
                name="测试服务器01",
                ipmi_ip="192.168.1.100",
                ipmi_username="admin",
                ipmi_password="admin123",
                ipmi_port=623,
                monitoring_enabled=False,  # 添加监控启用状态
                manufacturer="Dell",
                model="PowerEdge R740",
                serial_number="TEST001",
                description="用于测试的服务器实例",
                tags="test,demo",
                group_id=group_id_value
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