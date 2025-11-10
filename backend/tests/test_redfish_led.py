#!/usr/bin/env python3
"""
测试Redfish LED控制功能
"""

import asyncio
import sys
import os

# 添加项目路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ipmi import IPMIService

async def test_redfish_led_control():
    """测试Redfish LED控制功能"""
    ipmi_service = IPMIService()
    
    # 测试服务器信息（需要替换为实际的BMC信息）
    bmc_ip = "192.168.1.100"  # 替换为实际的BMC IP地址
    username = "admin"        # 替换为实际的用户名
    password = "password"     # 替换为实际的密码
    
    print(f"正在测试服务器 {bmc_ip} 的Redfish LED控制功能...")
    
    try:
        # 1. 获取LED状态
        print("1. 获取LED状态...")
        status_result = await ipmi_service.get_redfish_led_status(bmc_ip, username, password, timeout=10)
        print(f"   LED状态: {status_result}")
        
        # 2. 点亮LED
        print("2. 点亮LED...")
        turn_on_result = await ipmi_service.set_redfish_led_state(bmc_ip, username, password, "On", timeout=10)
        print(f"   点亮结果: {turn_on_result}")
        
        # 3. 再次获取LED状态
        print("3. 再次获取LED状态...")
        status_result2 = await ipmi_service.get_redfish_led_status(bmc_ip, username, password, timeout=10)
        print(f"   LED状态: {status_result2}")
        
        # 4. 关闭LED
        print("4. 关闭LED...")
        turn_off_result = await ipmi_service.set_redfish_led_state(bmc_ip, username, password, "Off", timeout=10)
        print(f"   关闭结果: {turn_off_result}")
        
        # 5. 最后获取LED状态
        print("5. 最后获取LED状态...")
        status_result3 = await ipmi_service.get_redfish_led_status(bmc_ip, username, password, timeout=10)
        print(f"   LED状态: {status_result3}")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_redfish_led_control())