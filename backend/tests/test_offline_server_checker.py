import asyncio
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_offline_server_checker():
    """测试离线服务器检查服务"""
    try:
        # 导入离线服务器检查服务
        from app.services.offline_server_checker import OfflineServerCheckerService
        
        logger.info("开始测试离线服务器检查服务...")
        
        # 创建服务实例
        checker_service = OfflineServerCheckerService()
        
        # 启动服务
        await checker_service.start()
        
        # 获取状态
        status = checker_service.get_status()
        logger.info(f"离线服务器检查服务状态: {status}")
        
        # 等待几分钟观察定时任务执行
        logger.info("离线服务器检查服务已启动，每2分钟会自动检查离线服务器")
        logger.info("按 Ctrl+C 停止测试")
        
        try:
            while True:
                await asyncio.sleep(10)
                status = checker_service.get_status()
                logger.info(f"当前状态: 运行中={status['running']}, 下次执行={status.get('next_run_time')}")
        except KeyboardInterrupt:
            logger.info("收到停止信号")
        
        # 停止服务
        await checker_service.stop()
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_offline_server_checker())