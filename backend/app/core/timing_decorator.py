import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

def timing_debug(func: Callable) -> Callable:
    """
    装饰器：为函数调用添加执行时间的debug日志
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        """异步函数包装器"""
        start_time = time.time()
        func_name = f"{func.__module__}.{func.__qualname__}"
        logger.debug(f"[调用时间] 开始执行 {func_name}")
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"[调用时间] {func_name} 执行完成，耗时: {execution_time:.4f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.debug(f"[调用时间] {func_name} 执行失败，耗时: {execution_time:.4f}秒，错误: {str(e)}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        """同步函数包装器"""
        start_time = time.time()
        func_name = f"{func.__module__}.{func.__qualname__}"
        logger.debug(f"[调用时间] 开始执行 {func_name}")
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"[调用时间] {func_name} 执行完成，耗时: {execution_time:.4f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.debug(f"[调用时间] {func_name} 执行失败，耗时: {execution_time:.4f}秒，错误: {str(e)}")
            raise
    
    # 根据函数是否为异步函数返回相应的包装器
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

# 为了兼容性，也导入asyncio
import asyncio