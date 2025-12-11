#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPMI连接池测试脚本
专门用于测试连接故障检查和重连功能
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
        logging.FileHandler('ipmi_connection_pool_test.log')
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

async def test_connection_validity():
    """测试连接有效性检查功能"""
    logger.info("=== 测试连接有效性检查功能 ===")
    
    # 这里我们只是展示连接有效性检查的逻辑
    # 实际的检查在IPMI连接池内部进行
    logger.info("连接有效性检查功能已在IPMIConnectionPool._is_connection_valid方法中实现")
    logger.info("检查项包括:")
    logger.info("1. 连接对象是否存在")
    logger.info("2. ipmi_session属性是否有效")
    logger.info("3. ipmi_session.broken状态检查")
    logger.info("4. 异常捕获兜底处理")

async def test_connection_recovery():
    """测试连接自动恢复功能"""
    logger.info("=== 测试连接自动恢复功能 ===")
    
    logger.info("连接自动恢复功能说明:")
    logger.info("1. 当检测到IPMI连接失效时，会自动从连接池中移除失效连接")
    logger.info("2. 在下次请求时会重新建立连接")
    logger.info("3. pyghmi库在检测到会话断开时会设置_fail_reason属性")
    logger.info("4. 连接池会处理'Session no longer connected'这类状态")

async def simulate_connection_failure_and_recovery(ip: str, username: str, password: str, port: int = 623):
    """模拟连接故障和恢复过程"""
    logger.info("=== 模拟连接故障和恢复过程 ===")
    
    try:
        # 第一次获取连接
        logger.info("1. 获取初始连接")
        conn1 = await ipmi_pool.get_connection(ip, username, password, port)
        logger.info(f"   成功获取连接: {conn1}")
        
        # 模拟使用连接
        logger.info("2. 使用连接获取电源状态")
        ipmi_service = IPMIService()
        power_state = await ipmi_service.get_power_state(ip, username, password, port)
        logger.info(f"   电源状态: {power_state}")
        
        # 模拟连接失效（通过手动移除连接）
        logger.info("3. 模拟连接失效")
        connection_key = f"{ip}:{port}:{username}"
        if connection_key in ipmi_pool.connections:
            removed_conn = ipmi_pool.connections.pop(connection_key)
            logger.info(f"   已移除连接: {removed_conn}")
            
            # 尝试关闭连接
            try:
                if hasattr(removed_conn, 'close'):
                    removed_conn.close()
                    logger.info("   已关闭失效连接")
            except Exception as e:
                logger.warning(f"   关闭失效连接时出错: {e}")
        
        # 再次获取连接（应该会重新建立）
        logger.info("4. 重新获取连接（测试自动恢复）")
        conn2 = await ipmi_pool.get_connection(ip, username, password, port)
        logger.info(f"   成功重新获取连接: {conn2}")
        
        # 验证是否是新的连接
        if conn1 != conn2:
            logger.info("   确认连接已重新建立（使用了新的连接对象）")
        else:
            logger.info("   使用了相同的连接对象")
            
        # 再次使用连接
        logger.info("5. 使用新连接获取电源状态")
        power_state2 = await ipmi_service.get_power_state(ip, username, password, port)
        logger.info(f"   电源状态: {power_state2}")
        
        logger.info("连接故障和恢复测试完成")
        
    except Exception as e:
        logger.error(f"连接故障和恢复测试失败: {e}")

async def test_concurrent_connections(ip: str, username: str, password: str, port: int = 623):
    """测试并发连接"""
    logger.info("=== 测试并发连接 ===")
    
    async def worker(worker_id: int):
        try:
            logger.info(f"Worker {worker_id} 开始工作")
            ipmi_service = IPMIService()
            
            # 多次获取电源状态
            for i in range(3):
                power_state = await ipmi_service.get_power_state(ip, username, password, port)
                logger.info(f"Worker {worker_id} 第 {i+1} 次获取电源状态: {power_state}")
                await asyncio.sleep(0.5)
                
            logger.info(f"Worker {worker_id} 完成工作")
            return True
        except Exception as e:
            logger.error(f"Worker {worker_id} 失败: {e}")
            return False
    
    # 创建多个并发任务
    tasks = [worker(i) for i in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    logger.info(f"并发连接测试完成，成功: {success_count}/{len(tasks)}")

async def periodic_connection_health_check(ip: str, username: str, password: str, port: int = 623, interval: int = 30):
    """定期检查连接健康状态"""
    global running
    
    logger.info(f"开始定期检查连接健康状态，间隔 {interval} 秒")
    
    check_count = 0
    success_count = 0
    failure_count = 0
    
    while running:
        check_count += 1
        try:
            start_time = datetime.now()
            logger.info(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] 第 {check_count} 次健康检查 - 开始检查")
            
            # 获取当前连接池状态
            pool_size = len(ipmi_pool.connections)
            logger.info(f"当前连接池大小: {pool_size}")
            
            # 显示连接详情
            for conn_key in ipmi_pool.connections:
                logger.info(f"  连接: {conn_key}")
                
            # 测试连接
            ipmi_service = IPMIService()
            power_state = await ipmi_service.get_power_state(ip, username, password, port)
            
            if power_state:
                success_count += 1
                logger.info(f"电源状态检查成功: {power_state}")
            else:
                failure_count += 1
                logger.warning("电源状态检查失败")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] 连接健康检查完成，耗时: {duration:.2f}秒")
            
            # 显示统计信息
            logger.info(f"统计信息 - 总检查: {check_count}, 成功: {success_count}, 失败: {failure_count}, 成功率: {success_count/check_count*100:.1f}%")
            
        except Exception as e:
            failure_count += 1
            logger.error(f"连接健康检查过程中发生错误: {e}")
        
        # 等待下一个周期
        logger.info(f"等待 {interval} 秒后进行下一次检查...")
        for i in range(interval):
            if not running:
                break
            await asyncio.sleep(1)
    
    logger.info(f"健康检查结束 - 总检查: {check_count}, 成功: {success_count}, 失败: {failure_count}, 成功率: {success_count/check_count*100:.1f}%")

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
    
    CHECK_INTERVAL = int(input("请输入检查间隔秒数 (默认: 30): ").strip() or "30")
    
    logger.info("IPMI连接池测试开始")
    logger.info(f"配置信息: IP={BMC_IP}, Username={BMC_USERNAME}, Port={BMC_PORT}")
    logger.info(f"检查间隔: {CHECK_INTERVAL} 秒")
    logger.info(f"IPMI超时设置: {settings.IPMI_TIMEOUT}秒")
    logger.info(f"连接池大小: {settings.IPMI_CONNECTION_POOL_SIZE}")
    
    try:
        # 测试连接有效性检查
        await test_connection_validity()
        
        # 测试连接恢复功能
        await test_connection_recovery()
        
        # 模拟连接故障和恢复
        await simulate_connection_failure_and_recovery(BMC_IP, BMC_USERNAME, BMC_PASSWORD, BMC_PORT)
        
        # 测试并发连接
        await test_concurrent_connections(BMC_IP, BMC_USERNAME, BMC_PASSWORD, BMC_PORT)
        
        # 开始定期健康检查
        logger.info("=== 开始定期健康检查 ===")
        await periodic_connection_health_check(BMC_IP, BMC_USERNAME, BMC_PASSWORD, BMC_PORT, CHECK_INTERVAL)
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
    finally:
        logger.info("测试结束，清理资源...")
        # 关闭连接池
        ipmi_pool.close()
        logger.info("资源清理完成")

if __name__ == "__main__":
    print("IPMI连接池测试工具")
    print("=" * 50)
    print("此工具将测试:")
    print("1. IPMI连接池的连接管理和故障恢复功能")
    print("2. 连接有效性检查")
    print("3. 并发连接处理")
    print("4. 定期健康检查")
    print("")
    print("按 Ctrl+C 可以随时停止测试")
    print("=" * 50)
    
    # 运行主函数
    asyncio.run(main())