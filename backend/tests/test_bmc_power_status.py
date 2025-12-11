#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BMC服务器电源状态定时获取测试脚本
用于测试IPMI连接池的连接故障检查和重连功能
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ipmi import ipmi_pool, IPMIService
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bmc_power_status_test.log')
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
    
    # 记录连接池初始状态
    initial_pool_size = len(ipmi_pool.connections)
    logger.info(f"初始连接池大小: {initial_pool_size}")
    
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
                
            # 显示连接池状态
            current_pool_size = len(ipmi_pool.connections)
            logger.info(f"当前连接池大小: {current_pool_size}")
                
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

async def test_connection_pool_management(ip: str, username: str, password: str, port: int = 623):
    """测试连接池管理功能"""
    logger.info("开始测试连接池管理功能")
    
    try:
        # 测试多次连接获取
        for i in range(3):
            logger.info(f"第 {i+1} 次获取连接")
            conn = await ipmi_pool.get_connection(ip, username, password, port)
            logger.info(f"成功获取连接: {conn}")
            
            # 检查连接有效性
            is_valid = ipmi_pool._is_connection_valid(conn)
            logger.info(f"连接有效性检查结果: {is_valid}")
            
            await asyncio.sleep(1)
            
        logger.info("连接池管理功能测试完成")
        
    except Exception as e:
        logger.error(f"连接池管理功能测试失败: {e}")

async def test_connection_failure_recovery(ip: str, username: str, password: str, port: int = 623):
    """测试连接故障恢复功能"""
    logger.info("开始测试连接故障恢复功能")
    
    try:
        # 正常获取连接
        logger.info("1. 正常获取连接")
        conn1 = await ipmi_pool.get_connection(ip, username, password, port)
        logger.info(f"   成功获取连接: {conn1}")
        
        # 模拟连接失效
        logger.info("2. 模拟连接失效")
        connection_key = f"{ip}:{port}:{username}"
        if connection_key in ipmi_pool.connections:
            # 移除连接但不关闭，模拟连接失效
            ipmi_pool.connections.pop(connection_key)
            logger.info("   已移除连接（模拟失效）")
        
        # 再次获取连接，应该会重新建立
        logger.info("3. 重新获取连接（测试自动恢复）")
        conn2 = await ipmi_pool.get_connection(ip, username, password, port)
        logger.info(f"   成功重新获取连接: {conn2}")
        
        logger.info("连接故障恢复功能测试完成")
        
    except Exception as e:
        logger.error(f"连接故障恢复功能测试失败: {e}")

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
    
    logger.info("BMC服务器电源状态定时获取测试开始")
    logger.info(f"配置信息: IP={BMC_IP}, Username={BMC_USERNAME}, Port={BMC_PORT}")
    logger.info(f"检查间隔: {CHECK_INTERVAL} 秒")
    logger.info(f"IPMI超时设置: {settings.IPMI_TIMEOUT}秒")
    logger.info(f"连接池大小: {settings.IPMI_CONNECTION_POOL_SIZE}")
    
    try:
        # 首先测试单次连接和电源状态获取
        logger.info("=== 单次连接测试 ===")
        await test_single_power_status(BMC_IP, BMC_USERNAME, BMC_PASSWORD, BMC_PORT)
        
        # 测试连接池管理
        logger.info("=== 连接池管理测试 ===")
        await test_connection_pool_management(BMC_IP, BMC_USERNAME, BMC_PASSWORD, BMC_PORT)
        
        # 测试连接故障恢复
        logger.info("=== 连接故障恢复测试 ===")
        await test_connection_failure_recovery(BMC_IP, BMC_USERNAME, BMC_PASSWORD, BMC_PORT)
        
        # 开始定时检查
        logger.info("=== 开始定时检查 ===")
        await periodic_power_status_check(BMC_IP, BMC_USERNAME, BMC_PASSWORD, BMC_PORT, CHECK_INTERVAL)
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
    finally:
        logger.info("测试结束，清理资源...")
        # 关闭连接池
        ipmi_pool.close()
        logger.info("资源清理完成")

if __name__ == "__main__":
    print("BMC服务器电源状态定时获取测试工具")
    print("=" * 50)
    print("此工具将测试:")
    print("1. 定时获取BMC服务器电源状态")
    print("2. IPMI连接池的连接管理和故障恢复功能")
    print("3. 连接有效性检查")
    print("")
    print("按 Ctrl+C 可以随时停止测试")
    print("=" * 50)
    
    # 运行主函数
    asyncio.run(main())