#!/usr/bin/env python3
"""
测试IPMI服务改进的脚本
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.ipmi import IPMIService
from app.core.exceptions import IPMIError

async def test_ipmi_service_improvements():
    """测试IPMI服务的改进功能"""
    print("测试IPMI服务改进功能")
    
    # 创建IPMI服务实例
    ipmi_service = IPMIService()
    
    # 检查服务实例是否创建成功
    print(f"IPMI服务实例创建成功: {ipmi_service}")
    
    # 检查新增的属性是否存在
    if hasattr(ipmi_service, '_semaphore'):
        print("✓ 信号量已正确添加")
    else:
        print("✗ 信号量缺失")
    
    if hasattr(ipmi_service, '_executor'):
        print("✓ 独立线程池已正确添加")
    else:
        print("✗ 独立线程池缺失")
    
    # 检查方法是否存在
    methods_to_check = ['close']
    for method in methods_to_check:
        if hasattr(ipmi_service, method):
            print(f"✓ 方法 {method} 存在")
        else:
            print(f"✗ 方法 {method} 不存在")
    
    # 测试资源释放
    try:
        ipmi_service.close()
        print("✓ 资源释放方法执行成功")
    except Exception as e:
        print(f"✗ 资源释放方法执行失败: {e}")
    
    print("IPMI服务改进功能测试完成")

if __name__ == "__main__":
    asyncio.run(test_ipmi_service_improvements())