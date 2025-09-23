import asyncio
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 测试定时任务服务
async def test_scheduler():
    try:
        from app.services.scheduler_service import scheduler_service
        
        logger.info("开始测试定时任务服务...")
        
        # 启动定时任务
        await scheduler_service.start()
        
        # 获取状态
        status = scheduler_service.get_status()
        logger.info(f"定时任务状态: {status}")
        
        # 等待几分钟观察定时任务执行
        logger.info("定时任务已启动，每分钟会自动刷新服务器电源状态")
        logger.info("按 Ctrl+C 停止测试")
        
        try:
            while True:
                await asyncio.sleep(10)
                status = scheduler_service.get_status()
                logger.info(f"当前状态: 运行中={status['running']}, 下次执行={status.get('next_run_time')}")
        except KeyboardInterrupt:
            logger.info("收到停止信号")
        
        # 停止定时任务
        await scheduler_service.stop()
        logger.info("测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scheduler())