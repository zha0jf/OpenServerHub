#!/usr/bin/env python
"""初始化审计日志表"""
import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import engine
from app.models import Base

# 创建所有表
print("正在创建数据库表...")
Base.metadata.create_all(bind=engine)
print("✓ 数据库表创建完成")
print("✓ 审计日志表已创建")
