#!/usr/bin/env python3
"""
测试Redfish支持检查功能并验证数据库更新
"""

import asyncio
import sys
import os

# 添加项目路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ipmi import IPMIService
from app.models.server import Server
from app.core.database import SessionLocal

async def test_redfish_check_and_db_update():
    """测试Redfish支持检查功能并验证数据库更新"""
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 获取一个测试服务器（这里假设ID为1的服务器存在）
        server = db.query(Server).filter(Server.id == 1).first()
        if not server:
            print("测试服务器不存在，请先创建一个服务器")
            return
        
        print(f"测试服务器: {server.name} ({server.ipmi_ip})")
        
        # 创建IPMI服务实例
        ipmi_service = IPMIService()
        
        # 检查Redfish支持情况
        print("正在检查Redfish支持情况...")
        redfish_result = await ipmi_service.check_redfish_support(
            bmc_ip=server.ipmi_ip,
            timeout=10
        )
        
        print(f"Redfish检查结果:")
        print(f"  支持: {redfish_result['supported']}")
        if redfish_result['supported']:
            print(f"  版本: {redfish_result['version']}")
        else:
            print(f"  错误: {redfish_result['error']}")
        
        # 更新数据库中的Redfish信息
        server.redfish_supported = redfish_result['supported']
        if redfish_result['supported']:
            server.redfish_version = redfish_result['version']
        
        db.commit()
        print("数据库更新完成")
        
        # 验证数据库更新
        updated_server = db.query(Server).filter(Server.id == 1).first()
        print(f"数据库中的Redfish信息:")
        print(f"  支持: {updated_server.redfish_supported}")
        print(f"  版本: {updated_server.redfish_version}")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_redfish_check_and_db_update())