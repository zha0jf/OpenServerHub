#!/usr/bin/env python3
"""
测试Redfish支持检查功能
"""

import asyncio
import sys
import os
import argparse

# 添加项目路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ipmi import IPMIService

async def test_redfish_check(bmc_ip):
    """测试Redfish支持检查功能"""
    ipmi_service = IPMIService()
    
    print(f"正在检查BMC {bmc_ip} 是否支持Redfish...")
    
    try:
        result = await ipmi_service.check_redfish_support(bmc_ip, timeout=10)
        
        print(f"检查结果:")
        print(f"  支持Redfish: {result['supported']}")
        if result['supported']:
            print(f"  Redfish版本: {result['version']}")
            print(f"  服务根信息: {result['service_root']}")
        else:
            print(f"  错误信息: {result['error']}")
            
    except Exception as e:
        print(f"检查过程中发生错误: {e}")

def main():
    parser = argparse.ArgumentParser(description='测试Redfish支持检查功能')
    parser.add_argument('bmc_ip', help='BMC IP地址')
    
    args = parser.parse_args()
    
    asyncio.run(test_redfish_check(args.bmc_ip))

if __name__ == "__main__":
    main()