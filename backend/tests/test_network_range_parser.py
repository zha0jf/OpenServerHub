"""
测试网络范围解析功能，验证支持多种格式
"""
import ipaddress
from typing import List
import logging

logger = logging.getLogger(__name__)

def parse_network_range(network: str) -> List[str]:
    """解析网络范围，支持多种格式
    
    支持的格式:
    - CIDR: 192.168.1.0/24
    - 范围: 192.168.1.1-192.168.1.100
    - 单个IP: 192.168.1.1
    - 逗号分隔多个IP: 192.168.1.1,192.168.1.2,192.168.1.3
    """
    ip_list = []
    
    try:
        # 检查是否包含逗号（多个IP地址）
        if "," in network:
            # 逗号分隔的多个IP地址
            ip_addresses = [ip.strip() for ip in network.split(",")]
            for ip in ip_addresses:
                if ip:  # 跳过空字符串
                    # 验证每个IP地址格式
                    ipaddress.IPv4Address(ip)
                    ip_list.append(ip)
        elif "/" in network:
            # CIDR格式: 192.168.1.0/24
            network_obj = ipaddress.IPv4Network(network, strict=False)
            # 排除网络地址和广播地址
            ip_list = [str(ip) for ip in network_obj.hosts()]
        elif "-" in network:
            # 范围格式: 192.168.1.1-192.168.1.100
            start_ip, end_ip = network.split("-", 1)
            start_ip = start_ip.strip()
            end_ip = end_ip.strip()
            
            start = ipaddress.IPv4Address(start_ip)
            end = ipaddress.IPv4Address(end_ip)
            
            if start > end:
                raise ValueError("起始IP不能大于结束IP")
            
            start_int = int(start)
            end_int = int(end)
            for val in range(start_int, end_int + 1):
                ip_list.append(str(ipaddress.IPv4Address(val)))
        else:
            # 单个IP地址
            ipaddress.IPv4Address(network)  # 验证IP格式
            ip_list = [network]
            
    except Exception as e:
        logger.error(f"解析网络范围失败: {network}, 错误: {str(e)}")
        return []
    
    return ip_list

def test_parse_network_range():
    """测试parse_network_range方法支持的各种格式"""
    
    print("\n=== 测试网络范围解析功能 ===\n")
    
    # 测试1: CIDR格式
    print("1. 测试CIDR格式 (192.168.1.0/24)")
    result = parse_network_range("192.168.1.0/24")
    print(f"   解析结果：{len(result)} 个IP")
    print(f"   范围：{result[0]} - {result[-1]}")
    assert len(result) > 0, "CIDR解析失败"
    assert result[0] == "192.168.1.1"
    assert result[-1] == "192.168.1.254"
    print("   ✓ 通过\n")
    
    # 测试2: IP范围格式
    print("2. 测试范围格式 (192.168.1.1-192.168.1.5)")
    result = parse_network_range("192.168.1.1-192.168.1.5")
    print(f"   解析结果：{len(result)} 个IP")
    print(f"   IP列表：{result}")
    assert len(result) == 5, f"范围解析失败，期望5个IP，实际{len(result)}个"
    assert result == ["192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.4", "192.168.1.5"]
    print("   ✓ 通过\n")
    
    # 测试3: 单个IP
    print("3. 测试单个IP (192.168.1.100)")
    result = parse_network_range("192.168.1.100")
    print(f"   解析结果：{result}")
    assert len(result) == 1, f"单IP解析失败，期望1个IP，实际{len(result)}个"
    assert result[0] == "192.168.1.100"
    print("   ✓ 通过\n")
    
    # 测试4: 逗号分隔多个IP（新增功能）
    print("4. 测试逗号分隔多个IP (192.168.1.1,192.168.1.2,192.168.1.3)")
    result = parse_network_range("192.168.1.1,192.168.1.2,192.168.1.3")
    print(f"   解析结果：{len(result)} 个IP")
    print(f"   IP列表：{result}")
    assert len(result) == 3, f"逗号分隔解析失败，期望3个IP，实际{len(result)}个"
    assert result == ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
    print("   ✓ 通过\n")
    
    # 测试5: 逗号分隔多个IP with spaces
    print("5. 测试逗号分隔多个IP with空格 (192.168.1.1, 192.168.1.2, 192.168.1.3)")
    result = parse_network_range("192.168.1.1, 192.168.1.2, 192.168.1.3")
    print(f"   解析结果：{len(result)} 个IP")
    print(f"   IP列表：{result}")
    assert len(result) == 3, f"带空格的逗号分隔解析失败，期望3个IP，实际{len(result)}个"
    assert result == ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
    print("   ✓ 通过\n")
    
    # 测试6: 多个IP地址（混合场景）
    print("6. 测试多个IP地址 (192.168.1.10,192.168.2.20,10.0.0.5)")
    result = parse_network_range("192.168.1.10,192.168.2.20,10.0.0.5")
    print(f"   解析结果：{len(result)} 个IP")
    print(f"   IP列表：{result}")
    assert len(result) == 3, f"多个IP解析失败，期望3个IP，实际{len(result)}个"
    assert result == ["192.168.1.10", "192.168.2.20", "10.0.0.5"]
    print("   ✓ 通过\n")
    
    # 测试7: 无效IP验证（应该返回空列表）
    print("7. 测试无效IP地址 (192.168.1.1,invalid.ip.address)")
    result = parse_network_range("192.168.1.1,invalid.ip.address")
    print(f"   解析结果：{result}")
    assert len(result) == 0, f"无效IP应该返回空列表，实际返回{len(result)}个IP"
    print("   ✓ 通过（正确拒绝无效IP）\n")
    
    print("=== 所有测试通过！ ===\n")

if __name__ == "__main__":
    try:
        test_parse_network_range()
        print("✓ 网络范围解析功能测试成功")
        exit(0)
    except AssertionError as e:
        print(f"✗ 测试失败: {e}")
        exit(1)
    except Exception as e:
        print(f"✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
