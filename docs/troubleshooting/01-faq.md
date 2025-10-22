# 常见问题解答 (FAQ)

## 部署相关问题

### Q1: Docker部署时Prometheus无法采集数据怎么办？

**症状**: Prometheus启动正常，但无法从IPMI Exporter采集数据

**解决方案**:
1. 检查网络连通性
```bash
# 进入Prometheus容器
docker exec -it prometheus_container_name sh
# 测试连接
wget -qO- http://ipmi-exporter:9290/metrics
```

2. 检查IPMI Exporter配置
```bash
# 查看IPMI Exporter日志
docker logs ipmi-exporter
# 检查配置文件
cat monitoring/ipmi-exporter/ipmi_local.yml
```

3. 验证BMC连接
```bash
# 手动测试IPMI连接
ipmitool -I lanplus -H <BMC_IP> -U <username> -P <password> power status
```

### Q2: Grafana仪表板无法显示数据

**症状**: Grafana界面正常，但图表无数据

**排查步骤**:
1. 检查Prometheus数据源配置
```
Grafana -> Configuration -> Data Sources -> Prometheus
URL: http://prometheus:9090
```

2. 验证Prometheus查询
```promql
# 在Prometheus Web界面测试查询
ipmi_temperature_celsius{instance=~".*"}
```

3. 检查时间范围设置
- 确保时间范围内有数据
- 检查时区设置

### Q3: AlertManager告警不发送邮件

**症状**: 告警触发但未收到邮件通知

**解决方案**:
1. 检查SMTP配置
```yaml
# monitoring/alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'  # 使用应用专用密码
```

2. 测试SMTP连接
```bash
# 进入AlertManager容器测试
telnet smtp.gmail.com 587
```

## 开发相关问题

### Q4: FastAPI应用启动失败

**常见错误及解决方案**:

**错误1**: `ModuleNotFoundError: No module named 'app'`
```bash
# 解决方案：检查PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"
# 或使用相对导入
cd backend && python -m app.main
```

**错误2**: `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table`
```bash
# 解决方案：运行数据库迁移
cd backend
alembic upgrade head
```

**错误3**: `pyghmi连接超时`
```python
# 解决方案：调整超时设置
conn = command.Command(
    bmc=host,
    userid=username,
    password=password,
    timeout=30  # 增加超时时间
)
```

### Q5: React前端无法连接后端API

**症状**: 前端请求后端API返回CORS错误

**解决方案**:
1. 检查FastAPI CORS配置
```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

2. 检查环境变量配置
```bash
# 前端.env文件
REACT_APP_API_URL=http://localhost:8080
REACT_APP_GRAFANA_URL=http://localhost:3001
```

### Q6: IPMI连接池耗尽

**症状**: 大量并发IPMI操作时出现连接失败

**解决方案**:
1. 调整连接池大小
```python
# app/services/ipmi_service.py
class IPMIConnectionPool:
    def __init__(self, max_connections=100):  # 增加连接数
        self.max_connections = max_connections
```

2. 实现连接复用和清理
```python
async def cleanup_stale_connections(self):
    """清理过期连接"""
    current_time = time.time()
    for key, conn_info in list(self.pool.items()):
        if current_time - conn_info['last_used'] > 300:  # 5分钟未使用
            del self.pool[key]
```

## 监控相关问题

### Q7: IPMI Exporter采集数据不准确

**症状**: 传感器数据显示异常值或NaN

**解决方案**:
1. 检查BMC固件版本
```bash
ipmitool -I lanplus -H <BMC_IP> -U <username> -P <password> mc info
```

2. 排除特定传感器
```yaml
# ipmi_local.yml
modules:
  default:
    collectors:
    - bmc
    - ipmi
    - dcmi
    - chassis
    exclude_sensor_ids:
    - 2    # 排除有问题的传感器ID
    - 15
```

3. 使用厂商特定模块
```yaml
# 针对Dell服务器
modules:
  dell:
    collectors:
    - bmc
    - ipmi
    - dcmi
    - chassis
    - sel
    ipmi:
      driver: "LAN_2_0"
      privilege: "user"
```

### Q8: Prometheus存储空间增长过快

**症状**: 磁盘空间快速消耗

**解决方案**:
1. 调整数据保留策略
```yaml
# prometheus.yml
global:
  scrape_interval: 60s  # 增加采集间隔
  
command:
  - '--storage.tsdb.retention.time=30d'  # 保留30天
  - '--storage.tsdb.retention.size=10GB'  # 限制大小
```

2. 清理无用指标
```yaml
metric_relabel_configs:
  - source_labels: [__name__]
    regex: 'unwanted_metric_.*'
    action: drop
```

## 性能相关问题

### Q9: 服务器列表加载缓慢

**症状**: 200台服务器列表加载时间超过10秒

**解决方案**:
1. 实现虚拟滚动
```tsx
// 使用react-window
import { FixedSizeList } from 'react-window';

const ServerList = ({ servers }) => (
  <FixedSizeList
    height={600}
    itemCount={servers.length}
    itemSize={80}
  >
    {({ index, style }) => (
      <div style={style}>
        <ServerCard server={servers[index]} />
      </div>
    )}
  </FixedSizeList>
);
```

2. 实现分页加载
```python
# 后端分页查询
@router.get("/servers")
async def get_servers(
    page: int = 1,
    size: int = 50,  # 每页50条
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * size
    servers = await get_servers_paginated(db, offset, size)
    return {"data": servers, "total": total_count}
```

## 安全相关问题

### Q10: BMC密码安全存储

**问题**: 如何安全存储BMC密码？

**解决方案**:
使用强加密算法
```python
from cryptography.fernet import Fernet
import os

class PasswordEncryption:
    def __init__(self):
        # 从环境变量获取密钥
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
    
    def encrypt_password(self, password: str) -> str:
        return self.cipher.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        return self.cipher.decrypt(encrypted_password.encode()).decode()
```

### Q11: API接口安全防护

**问题**: 如何防止API接口被恶意调用？

**解决方案**:
实现速率限制
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/servers/{server_id}/power/{action}")
@limiter.limit("10/minute")  # 每分钟最多10次
async def power_control(request: Request, server_id: int, action: str):
    # 电源控制逻辑
    pass
```

## 故障排查工具

### 系统诊断脚本

```bash
#!/bin/bash
# scripts/diagnose.sh - 系统诊断脚本

echo "=== OpenServerHub 系统诊断 ==="

# 检查Docker容器状态
echo "1. 检查容器状态..."
docker-compose ps

# 检查网络连通性
echo "2. 检查网络连通性..."
docker exec backend ping -c 3 prometheus
docker exec backend ping -c 3 grafana

# 检查Prometheus数据
echo "3. 检查Prometheus数据..."
curl -s "http://localhost:9090/api/v1/targets" | jq '.data.activeTargets[] | {job: .job, health: .health}'

echo "=== 诊断完成 ==="
```

### 日志收集脚本

```bash
#!/bin/bash
# scripts/collect_logs.sh - 日志收集脚本

LOG_DIR="./logs/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "收集系统日志到: $LOG_DIR"

# 收集容器日志
docker-compose logs --no-color > "$LOG_DIR/docker-compose.log"
docker logs backend > "$LOG_DIR/backend.log" 2>&1
docker logs prometheus > "$LOG_DIR/prometheus.log" 2>&1
docker logs grafana > "$LOG_DIR/grafana.log" 2>&1

# 收集配置文件
cp -r monitoring/ "$LOG_DIR/"
cp docker-compose.yml "$LOG_DIR/"

# 打包日志
tar -czf "openshub_logs_$(date +%Y%m%d_%H%M%S).tar.gz" -C logs .

echo "日志收集完成"
```

## 联系支持

如果以上解决方案无法解决您的问题，请：

1. **提交Issue**: 在GitHub项目页面提交详细的问题描述
2. **邮件联系**: 发送邮件至 support@openshub.com
3. **社区讨论**: 加入项目讨论群组

**提交问题时请包含**:
- 系统环境信息（操作系统、Docker版本等）
- 详细的错误信息和日志
- 复现步骤
- 相关配置文件（注意隐藏敏感信息）