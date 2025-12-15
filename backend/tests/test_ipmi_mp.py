#!/usr/bin/env python3
"""
简单的IPMI多进程实现测试脚本
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.ipmi import IPMIService
from app.core.exceptions import IPMIError

async def test_ipmi_mp():
    """测试多进程IPMI实现"""
    print("测试多进程IPMI实现")
    
    # 创建IPMI服务实例
    ipmi_service = IPMIService()
    
    # 检查服务实例是否创建成功
    print(f"IPMI服务实例创建成功: {ipmi_service}")
    
    # 检查服务类的方法是否存在
    methods_to_check = [
        'get_power_state',
        'power_control',
        'get_system_info',
        'get_sensor_data',
        'get_users',
        'create_user',
        'set_user_priv',
        'set_user_password',
        'test_connection'
    ]
    
    for method in methods_to_check:
        if hasattr(ipmi_service, method):
            print(f"✓ 方法 {method} 存在")
        else:
            print(f"✗ 方法 {method} 不存在")
    
    print("多进程IPMI实现测试完成")

if __name__ == "__main__":
    asyncio.run(test_ipmi_mp())