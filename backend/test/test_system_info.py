#!/usr/bin/env python3
"""
测试系统信息获取的脚本
"""
import sqlite3
import requests
import json
from datetime import datetime

def test_system_info_update():
    """测试系统信息更新"""
    # 首先查看当前数据库状态
    print("=== 当前数据库状态 ===")
    conn = sqlite3.connect('openshub.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, ipmi_ip, manufacturer, model, serial_number, updated_at FROM servers WHERE id = 4')
    result = cursor.fetchone()
    print(f'Server ID: {result[0]}')
    print(f'Name: {result[1]}')
    print(f'IPMI IP: {result[2]}')
    print(f'Manufacturer: {result[3]}')
    print(f'Model: {result[4]}')
    print(f'Serial: {result[5]}')
    print(f'Updated: {result[6]}')
    conn.close()
    
    # 尝试调用状态更新API（需要认证）
    print("\n=== 尝试调用状态更新API ===")
    try:
        # 注意：这需要正确的认证，可能会失败
        response = requests.post('http://localhost:8000/api/v1/servers/4/status')
        print(f'Status Code: {response.status_code}')
        print(f'Response: {response.text}')
        
        if response.status_code == 401:
            print("需要认证 - 这是正常的")
        elif response.status_code == 200:
            print("状态更新成功！")
        else:
            print(f"意外状态码: {response.status_code}")
            
    except Exception as e:
        print(f"API调用失败: {e}")
    
    print("\n=== 检查是否有更新 ===")
    # 再次查看数据库状态
    conn = sqlite3.connect('openshub.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, ipmi_ip, manufacturer, model, serial_number, updated_at FROM servers WHERE id = 4')
    result = cursor.fetchone()
    print(f'Updated: {result[6]}')
    print(f'Current: {datetime.now()}')
    conn.close()

if __name__ == "__main__":
    test_system_info_update()