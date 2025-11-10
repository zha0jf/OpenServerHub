#!/usr/bin/env python3
"""
测试Redfish LED控制功能
"""

import asyncio
import sys
import os
import argparse

# 添加项目路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ipmi import IPMIService

async def test_redfish_led_control(bmc_ip, username, password):
    """测试Redfish LED控制功能"""
    ipmi_service = IPMIService()
    
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

def main():
    parser = argparse.ArgumentParser(description='测试Redfish LED控制功能')
    parser.add_argument('bmc_ip', help='BMC IP地址')
    parser.add_argument('username', help='用户名')
    parser.add_argument('password', help='密码')
    
    args = parser.parse_args()
    
    asyncio.run(test_redfish_led_control(args.bmc_ip, args.username, args.password))

if __name__ == "__main__":
    main()