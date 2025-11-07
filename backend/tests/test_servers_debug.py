#!/usr/bin/env python3
"""
通用服务器FRU信息调试脚本
使用方法: python test_servers_debug.py <IP地址> [用户名] [密码]
默认用户名: root，默认密码: 0penBmc
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ipmi import IPMIService
from app.core.config import settings
import sqlite3

async def debug_server_fru(ip_address, username='root', password='0penBmc'):
    """调试指定IP地址的服务器FRU信息"""
    
    print(f"🔍 调试服务器: {ip_address}")
    print(f"用户名: {username}")
    print(f"密码: {password}")
    print("-" * 60)
    
    # 首先从数据库获取服务器基本信息
    try:
        conn = sqlite3.connect('d:\\workspace\\OpenServerHub\\backend\\openshub.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, ipmi_ip, manufacturer, model, serial_number, updated_at 
            FROM servers 
            WHERE ipmi_ip = ?
        ''', (ip_address,))
        server_info = cursor.fetchone()
        conn.close()
        
        if server_info:
            print("📊 数据库中当前信息:")
            print(f"  ID: {server_info[0]}")
            print(f"  名称: {server_info[1]}")
            print(f"  IP: {server_info[2]}")
            print(f"  制造商: {server_info[3]}")
            print(f"  型号: {server_info[4]}")
            print(f"  序列号: {server_info[5]}")
            print(f"  更新时间: {server_info[6]}")
            print()
        else:
            print("⚠️  该IP地址不在数据库中")
            print()
            
    except Exception as e:
        print(f"❌ 查询数据库失败: {e}")
        print()
    
    ipmi_service = IPMIService()
    
    try:
        # 获取系统信息
        print("🔄 正在通过IPMI获取系统信息...")
        try:
            # 使用asyncio.wait_for添加超时控制
            system_info = await asyncio.wait_for(
                ipmi_service.get_system_info(
                    ip=ip_address,
                    username=username,
                    password=password
                ),
                timeout=15.0  # 15秒超时
            )
        except asyncio.TimeoutError:
            print("❌ 获取系统信息超时")
            print("💡 可能原因:")
            print("   - 服务器IPMI服务无响应")
            print("   - 网络连接问题")
            return False
        except Exception as e:
            print(f"❌ 获取系统信息失败: {e}")
            print("💡 可能原因:")
            print("   - 服务器IPMI服务无响应")
            print("   - 网络连接问题")
            print("   - 用户名或密码错误")
            return False
        finally:
            # 显式关闭IPMI连接
            print("🔄 正在关闭IPMI连接...")
            try:
                # 显式关闭所有pyghmi连接对象
                for conn_key, conn in ipmi_service.pool.connections.items():
                    try:
                        if hasattr(conn, 'close') and callable(getattr(conn, 'close')):
                            conn.close()
                    except Exception as e:
                        print(f"⚠️  关闭连接 {conn_key} 时出错: {e}")
                
                # 清空连接池中的所有连接
                ipmi_service.pool.connections.clear()
                print("✅ IPMI连接已关闭")
                
                # 强制取消所有未完成的异步任务
                for task in asyncio.all_tasks():
                    if task is not asyncio.current_task() and not task.done():
                        task.cancel()
                print("✅ 异步任务已清理")
            except Exception as close_e:
                print(f"⚠️  关闭IPMI连接时出错: {close_e}")
        
        print("✅ 成功获取系统信息:")
        print(f"  制造商: {system_info.get('manufacturer', 'Unknown')}")
        print(f"  产品: {system_info.get('product', 'Unknown')}")
        print(f"  序列号: {system_info.get('serial', 'Unknown')}")
        print(f"  BMC版本: {system_info.get('bmc_version', 'Unknown')}")
        print(f"  BMC IP: {system_info.get('bmc_ip', 'Unknown')}")
        print(f"  BMC MAC: {system_info.get('bmc_mac', 'Unknown')}")
        print()
        
        # 对比分析
        print("\n🔍 对比分析:")
        if system_info.get('manufacturer') == 'Unknown':
            print("❌ 系统未能正确解析FRU信息")
            print("💡 建议: 检查IPMIService中的FRU字段映射逻辑")
        else:
            print("✅ 系统成功解析FRU信息")
            
        # 检查是否有中文编码问题
        manufacturer = system_info.get('manufacturer', '')
        if any(ord(c) > 127 for c in manufacturer):
            print("⚠️  检测到可能的编码问题")
            
    except Exception as e:
        print(f"❌ 获取系统信息失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def print_usage():
    """打印使用说明"""
    print("使用方法:")
    print("  python test_servers_debug.py <IP地址> [用户名] [密码]")
    print("示例:")
    print("  python test_servers_debug.py 10.10.0.146")
    print("  python test_servers_debug.py 10.10.0.146 root 0penBmc")
    print("  python test_servers_debug.py 10.10.0.146 admin password123")

async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    ip_address = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else 'root'
    password = sys.argv[3] if len(sys.argv) > 3 else '0penBmc'
    
    print(f"🚀 开始调试服务器 {ip_address}")
    print("=" * 60)
    
    try:
        success = await debug_server_fru(ip_address, username, password)
        
        print("=" * 60)
        if success:
            print("✅ 调试完成")
        else:
            print("❌ 调试失败")
    except Exception as e:
        print("=" * 60)
        print(f"❌ 调试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序异常退出: {e}")
    finally:
        print("👋 程序结束")
        # 强制清理所有资源并退出
        import gc
        import threading
        
        # 清理所有线程
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                try:
                    thread.join(timeout=0.1)
                except:
                    pass
        
        # 强制垃圾回收
        gc.collect()
        
        # 确保程序退出
        os._exit(0)