#!/usr/bin/env python
"""运行数据库迁移"""
import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from alembic.config import Config
from alembic import command

# 运行迁移
cfg = Config('alembic.ini')
command.upgrade(cfg, 'head')
print("✓ 数据库迁移完成")
