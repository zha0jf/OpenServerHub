#!/usr/bin/env python3
"""
简单的IPMI服务测试脚本
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__)))

# 测试导入
try:
    from app.services.ipmi import IPMIService, _run_task_in_fresh_process_safe
    print("✓ IPMI服务导入成功")
    
    # 测试创建实例
    service = IPMIService()
    print("✓ IPMI服务实例创建成功")
    
    # 检查新增属性
    if hasattr(service, '_semaphore'):
        print("✓ 信号量属性存在")
    else:
        print("✗ 信号量属性缺失")
        
    if hasattr(service, '_executor'):
        print("✓ 线程池属性存在")
    else:
        print("✗ 线程池属性缺失")
    
    # 测试资源释放方法
    if hasattr(service, 'close'):
        print("✓ close方法存在")
    else:
        print("✗ close方法缺失")
        
    # 测试安全进程函数
    import inspect
    sig = inspect.signature(_run_task_in_fresh_process_safe)
    params = list(sig.parameters.keys())
    if 'timeout' in params:
        print("✓ _run_task_in_fresh_process_safe函数支持timeout参数")
    else:
        print("✗ _run_task_in_fresh_process_safe函数不支持timeout参数")
    
    print("测试完成")
    
except Exception as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()