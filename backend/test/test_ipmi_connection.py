#!/usr/bin/env python3
"""
IPMI连接测试脚本
用于测试特定IP地址的IPMI连接和凭据
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.ipmi import IPMIService
from app.core.exceptions import IPMIError

async def test_ipmi_connection(ip: str, username: str, password: str, port: int = 623):
    """测试IPMI连接"""
    print(f"测试IPMI连接: {ip}:{port}")
    print(f"用户名: {username}")
    print(f"密码: {'*' * len(password) if password else '(空)'}")
    
    ipmi_service = IPMIService()
    
    try:
        # 测试连接
        print("正在测试连接...")
        result = await ipmi_service.test_connection(ip, username, password, port)
        print(f"连接测试结果: {result}")
        
        if result.get("status") == "success":
            # 获取系统信息
            print("正在获取系统信息...")
            system_info = await ipmi_service.get_system_info(ip, username, password, port, timeout=15)
            print(f"系统信息: {system_info}")
            
            # 获取传感器数据
            print("正在获取传感器数据...")
            sensor_data = await ipmi_service.get_sensor_data(ip, username, password, port)
            print(f"传感器数据获取成功，温度传感器数量: {len(sensor_data.get('temperature', []))}")
            
    except IPMIError as e:
        print(f"IPMI错误: {e}")
    except Exception as e:
        print(f"其他错误: {e}")

async def main():
    if len(sys.argv) < 4:
        print("用法: python test_ipmi_connection.py <IP> <用户名> <密码> [端口]")
        print("示例: python test_ipmi_connection.py 10.10.0.243 ADMIN ADMIN 623")
        return
    
    ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 623
    
    await test_ipmi_connection(ip, username, password, port)

if __name__ == "__main__":
    asyncio.run(main())