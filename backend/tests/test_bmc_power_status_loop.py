#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BMC服务器电源状态循环测试脚本
用于测试多进程IPMI实现的连接稳定性和电源状态获取功能
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ipmi import IPMIService
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bmc_power_status_loop_test.log')
    ]
)

logger = logging.getLogger(__name__)

# 全局变量用于控制程序运行
running = True

def signal_handler(sig, frame):
    """信号处理器，用于优雅地停止程序"""
    global running
    logger.info("收到停止信号，正在关闭程序...")
    running = False

async def test_single_power_status(ip: str, username: str, password: str, port: int = 623):
    """测试单次电源状态获取"""
    try:
        logger.info(f"开始测试获取服务器 {ip}:{port} 的电源状态")
        
        # 创建IPMI服务实例
        ipmi_service = IPMIService()
        
        # 获取电源状态
        power_state = await ipmi_service.get_power_state(
            ip=ip,
            username=username,
            password=password,
            port=port
        )
        
        logger.info(f"服务器 {ip}:{port} 的电源状态: {power_state}")
        return power_state
        
    except Exception as e:
        logger.error(f"获取服务器 {ip}:{port} 电源状态失败: {e}")
        return None

async def periodic_power_status_check(ip: str, username: str, password: str, port: int = 623, interval: int = 60):
    """定时获取电源状态"""
    global running
    
    logger.info(f"开始定时获取服务器 {ip}:{port} 的电源状态，间隔 {interval} 秒")
    
    check_count = 0
    success_count = 0
    failure_count = 0
    
    while running:
        check_count += 1
        try:
            # 获取当前时间
            start_time = datetime.now()
            logger.info(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] 第 {check_count} 次检查 - 开始获取电源状态")
            
            # 获取电源状态
            power_state = await test_single_power_status(ip, username, password, port)
            
            # 记录结果
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if power_state:
                success_count += 1
                logger.info(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 电源状态获取成功，耗时: {duration:.2f}秒，状态: {power_state}")
            else:
                failure_count += 1
                logger.warning(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 电源状态获取失败，耗时: {duration:.2f}秒")
                
        except Exception as e:
            failure_count += 1
            logger.error(f"定时获取电源状态过程中发生错误: {e}")
        
        # 显示统计信息
        logger.info(f"统计信息 - 总检查: {check_count}, 成功: {success_count}, 失败: {failure_count}, 成功率: {success_count/check_count*100:.1f}%")
        
        # 等待下一个周期
        logger.info(f"等待 {interval} 秒后进行下一次检查...")
        for i in range(interval):
            if not running:
                break
            await asyncio.sleep(1)
    
    logger.info(f"定时检查结束 - 总检查: {check_count}, 成功: {success_count}, 失败: {failure_count}, 成功率: {success_count/check_count*100:.1f}%")

async def main():
    """主函数"""
    global running
    
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # BMC服务器配置（请根据实际情况修改）
    BMC_IP = input("请输入BMC IP地址 (默认: 10.10.0.146): ").strip() or "10.10.0.146"
    BMC_USERNAME = input("请输入BMC用户名 (默认: admin): ").strip() or "admin"
    BMC_PASSWORD = input("请输入BMC密码 (默认: password): ").strip() or "password"
    BMC_PORT = int(input("请输入BMC端口 (默认: 623): ").strip() or "623")
    
    CHECK_INTERVAL = int(input("请输入检查间隔秒数 (默认: 60): ").strip() or "60")
    
    logger.info("BMC服务器电源状态循环测试开始")
    logger.info(f"配置信息: IP={BMC_IP}, Username={BMC_USERNAME}, Port={BMC_PORT}")
    logger.info(f"检查间隔: {CHECK_INTERVAL} 秒")
    logger.info(f"IPMI超时设置: {settings.IPMI_TIMEOUT}秒")
    
    try:
        # 首先测试单次连接和电源状态获取
        logger.info("=== 单次连接测试 ===")
        await test_single_power_status(BMC_IP, BMC_USERNAME, BMC_PASSWORD, BMC_PORT)
        
        # 开始定时检查
        logger.info("=== 开始定时检查 ===")
        await periodic_power_status_check(BMC_IP, BMC_USERNAME, BMC_PASSWORD, BMC_PORT, CHECK_INTERVAL)
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    print("BMC服务器电源状态循环测试工具")
    print("=" * 50)
    print("此工具将测试:")
    print("1. 定时获取BMC服务器电源状态")
    print("2. 多进程IPMI实现的连接稳定性")
    print("")
    print("按 Ctrl+C 可以随时停止测试")
    print("=" * 50)
    
    # 运行主函数
    asyncio.run(main())