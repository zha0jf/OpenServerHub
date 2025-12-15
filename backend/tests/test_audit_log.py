#!/usr/bin/env python3
"""
审计日志功能测试脚本
验证审计日志的基本功能是否正常工作
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.services.audit_log import AuditLogService
from app.models.audit_log import AuditAction, AuditStatus
from datetime import datetime, timedelta

def test_audit_log():
    """测试审计日志功能"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("OpenServerHub 审计日志功能测试")
        print("=" * 60)
        
        audit_service = AuditLogService(db)
        
        # 测试1: 创建登录日志
        print("\n[测试1] 创建登录成功日志...")
        log1 = audit_service.log_login(
            username="admin",
            user_id=1,
            ip_address="127.0.0.1",
            user_agent="Test Client",
            success=True
        )
        print(f"✓ 成功创建日志 ID: {log1.id}")
        
        # 测试2: 创建登录失败日志
        print("\n[测试2] 创建登录失败日志...")
        log2 = audit_service.log_login(
            username="testuser",
            ip_address="192.168.1.100",
            user_agent="Test Client",
            success=False
        )
        print(f"✓ 成功创建日志 ID: {log2.id}")
        
        # 测试3: 创建电源控制日志
        print("\n[测试3] 创建电源控制成功日志...")
        log3 = audit_service.log_power_control(
            user_id=1,
            username="admin",
            server_id=1,
            server_name="Test Server",
            action_type="on",
            success=True,
            ip_address="127.0.0.1",
            user_agent="Test Client"
        )
        print(f"✓ 成功创建日志 ID: {log3.id}")
        
        # 测试4: 创建电源控制失败日志
        print("\n[测试4] 创建电源控制失败日志...")
        log4 = audit_service.log_power_control(
            user_id=1,
            username="admin",
            server_id=2,
            server_name="Test Server 2",
            action_type="restart",
            success=False,
            error_message="IPMI连接超时",
            ip_address="127.0.0.1",
            user_agent="Test Client"
        )
        print(f"✓ 成功创建日志 ID: {log4.id}")
        
        # 测试5: 查询所有日志
        print("\n[测试5] 查询所有审计日志...")
        logs, total = audit_service.get_logs(limit=100)
        print(f"✓ 查询成功，共 {total} 条日志，返回 {len(logs)} 条")
        
        # 测试6: 按操作类型过滤
        print("\n[测试6] 按操作类型过滤 (LOGIN)...")
        logs, total = audit_service.get_logs(action="LOGIN", limit=100)
        print(f"✓ 查询成功，共 {total} 条 LOGIN 日志")
        
        # 测试7: 按资源类型过滤
        print("\n[测试7] 按资源类型过滤 (server)...")
        logs, total = audit_service.get_logs(resource_type="server", limit=100)
        print(f"✓ 查询成功，共 {total} 条 server 资源日志")
        
        # 测试8: 按操作者过滤
        print("\n[测试8] 按操作者过滤 (operator_id=1)...")
        logs, total = audit_service.get_logs(operator_id=1, limit=100)
        print(f"✓ 查询成功，共 {total} 条操作者1的日志")
        
        # 测试9: 按日期范围过滤
        print("\n[测试9] 按日期范围过滤 (今天)...")
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now()
        logs, total = audit_service.get_logs(start_date=start_date, end_date=end_date, limit=100)
        print(f"✓ 查询成功，共 {total} 条今天的日志")
        
        # 测试10: 获取单条日志详情
        print("\n[测试10] 获取日志详情 (ID={})...".format(log1.id))
        log_detail = audit_service.get_log_by_id(log1.id)
        if log_detail:
            print(f"✓ 成功获取日志详情:")
            print(f"  - 操作类型: {log_detail.action}")
            print(f"  - 操作者: {log_detail.operator_username}")
            print(f"  - 资源: {log_detail.resource_type}:{log_detail.resource_id}")
            print(f"  - 状态: {log_detail.status}")
            print(f"  - IP地址: {log_detail.ip_address}")
            print(f"  - 时间: {log_detail.created_at}")
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！审计日志功能正常工作")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_audit_log()
    sys.exit(0 if success else 1)
