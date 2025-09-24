# 监控系统部署指南

## 1. 概述

本文档详细说明如何部署 OpenServerHub 的监控系统组件，包括 Prometheus、AlertManager、Grafana 和 IPMI Exporter。

## 2. 系统要求

### 2.1 硬件要求
- CPU: 4核以上
- 内存: 8GB以上
- 磁盘: 50GB以上可用空间（用于监控数据存储）

### 2.2 软件要求
- Docker 20.10+
- Docker Compose 1.29+
- Linux/Windows/macOS 操作系统

## 3. 部署步骤

### 3.1 准备工作

1. 确保已克隆 OpenServerHub 项目：
```bash
git clone https://github.com/yourusername/OpenServerHub.git
cd OpenServerHub
```

2. 确保监控配置文件已存在：
```bash
ls -la monitoring/
```

### 3.2 启动监控系统

使用 Docker Compose 启动所有监控组件：

```bash
# 启动监控系统
docker-compose -f docker-compose.monitoring.yml up -d

# 查看运行状态
docker-compose -f docker-compose.monitoring.yml ps
```

### 3.3 验证部署

1. 访问 Prometheus: http://localhost:9090
2. 访问 AlertManager: http://localhost:9093
3. 访问 Grafana: http://localhost:3001

## 4. 配置说明

### 4.1 Prometheus 配置

Prometheus 配置文件位于 `monitoring/prometheus/prometheus.yml`：

```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s

scrape_configs:
  - job_name: 'openshub-api'
    static_configs:
      - targets: ['backend:8080']
  
  - job_name: 'ipmi-servers'
    file_sd_configs:
      - files:
        - '/etc/prometheus/targets/ipmi-targets.json'
```

### 4.2 AlertManager 配置

AlertManager 配置文件位于 `monitoring/alertmanager/alertmanager.yml`：

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@openshub.com'

route:
  group_by: ['alertname']
  receiver: 'default'

receivers:
  - name: 'default'
    email_configs:
      - to: 'admin@openshub.com'
```

### 4.3 Grafana 配置

Grafana 数据源配置位于 `monitoring/grafana/provisioning/datasources/prometheus.yml`：

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
```

## 5. IPMI Exporter 部署

### 5.1 单个 Exporter 部署

对于单台服务器，可以使用以下命令启动 IPMI Exporter：

```bash
docker run -d \
  --name ipmi-exporter-1 \
  -p 9290:9290 \
  -v /path/to/ipmi_local.yml:/config/ipmi_local.yml \
  prometheuscommunity/ipmi-exporter:v1.4.0 \
  --config.file=/config/ipmi_local.yml
```

### 5.2 多个 Exporter 批量部署

对于多台服务器，建议使用 Docker Compose 模板化部署。创建 `docker-compose.ipmi.yml`：

```yaml
version: '3.8'

services:
  ipmi-exporter-1:
    image: prometheuscommunity/ipmi-exporter:v1.4.0
    ports:
      - "9290:9290"
    volumes:
      - ./monitoring/ipmi-exporter/ipmi_local.yml:/config/ipmi_local.yml
    command:
      - '--config.file=/config/ipmi_local.yml'
    environment:
      - IPMI_HOST=192.168.1.100
      - IPMI_USERNAME=admin
      - IPMI_PASSWORD=password

  ipmi-exporter-2:
    image: prometheuscommunity/ipmi-exporter:v1.4.0
    ports:
      - "9291:9290"
    volumes:
      - ./monitoring/ipmi-exporter/ipmi_local.yml:/config/ipmi_local.yml
    command:
      - '--config.file=/config/ipmi_local.yml'
    environment:
      - IPMI_HOST=192.168.1.101
      - IPMI_USERNAME=admin
      - IPMI_PASSWORD=password
```

启动所有 IPMI Exporter：
```bash
docker-compose -f docker-compose.ipmi.yml up -d
```

## 6. 动态配置管理

### 6.1 Prometheus 目标配置

Prometheus 使用文件服务发现机制动态加载监控目标。目标配置文件位于 `monitoring/prometheus/targets/ipmi-targets.json`：

```json
[
  {
    "targets": ["192.168.1.100:9290"],
    "labels": {
      "server_id": "1",
      "server_name": "server-01"
    }
  }
]
```

### 6.2 自动同步配置

当在 OpenServerHub 中添加或删除服务器时，系统会自动更新 Prometheus 目标配置文件并通知 Prometheus 重新加载配置。

## 7. 告警规则配置

告警规则文件位于 `monitoring/prometheus/rules/hardware_alerts.yml`：

```yaml
groups:
  - name: server_hardware
    rules:
      - alert: HighCPUTemperature
        expr: ipmi_temperature_celsius > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU温度过高"
```

## 8. Grafana 仪表板

### 8.1 自动创建仪表板

系统会为每台服务器自动创建 Grafana 仪表板，包含以下面板：
- CPU 温度监控
- 风扇转速监控
- 电压监控

### 8.2 手动创建仪表板

访问 Grafana (http://localhost:3001) 并使用默认账号登录：
- 用户名: admin
- 密码: admin

然后可以手动创建自定义仪表板。

## 9. 监控数据保留策略

### 9.1 Prometheus 数据保留

默认情况下，Prometheus 会保留 90 天的监控数据。可以通过修改 `docker-compose.monitoring.yml` 中的参数来调整：

```yaml
command:
  - '--storage.tsdb.retention.time=180d'  # 保留180天数据
```

### 9.2 存储优化

为了优化存储使用，可以考虑以下策略：
1. 调整抓取间隔（较长的间隔会减少数据量）
2. 使用指标过滤（只收集关键指标）
3. 定期清理旧数据

## 10. 故障排查

### 10.1 查看日志

```bash
# 查看 Prometheus 日志
docker logs prometheus

# 查看 AlertManager 日志
docker logs alertmanager

# 查看 Grafana 日志
docker logs grafana
```

### 10.2 常见问题

1. **Prometheus 无法抓取数据**
   - 检查 IPMI Exporter 是否正常运行
   - 检查网络连接是否正常
   - 检查目标配置文件是否正确

2. **告警未触发**
   - 检查告警规则是否正确
   - 检查 AlertManager 配置是否正确
   - 查看 Prometheus 告警页面确认规则状态

3. **Grafana 无法显示数据**
   - 检查数据源配置是否正确
   - 检查 Prometheus 是否有数据
   - 检查查询语句是否正确

## 11. 性能调优

### 11.1 资源限制

在 `docker-compose.monitoring.yml` 中为各组件设置资源限制：

```yaml
services:
  prometheus:
    mem_limit: 4g
    cpus: 2.0
```

### 11.2 查询优化

1. 避免使用过于复杂的查询表达式
2. 合理设置抓取间隔
3. 使用指标标签进行数据分片

## 12. 安全配置

### 12.1 网络安全

1. 限制监控组件的网络访问
2. 使用 HTTPS 加密通信
3. 配置防火墙规则

### 12.2 认证安全

1. 修改默认密码
2. 使用强密码策略
3. 定期更新认证信息

## 13. 备份与恢复

### 13.1 Prometheus 数据备份

```bash
# 备份 Prometheus 数据
docker run --rm \
  -v prometheus_data:/prometheus \
  -v /backup/path:/backup \
  busybox tar czf /backup/prometheus_backup.tar.gz -C /prometheus .
```

### 13.2 Grafana 配置备份

```bash
# 备份 Grafana 数据
docker run --rm \
  -v grafana_data:/var/lib/grafana \
  -v /backup/path:/backup \
  busybox tar czf /backup/grafana_backup.tar.gz -C /var/lib/grafana .
```

## 14. 升级指南

### 14.1 组件升级

1. 备份现有配置和数据
2. 更新 Docker 镜像版本
3. 重启服务

```bash
# 拉取最新镜像
docker-compose -f docker-compose.monitoring.yml pull

# 重启服务
docker-compose -f docker-compose.monitoring.yml up -d
```

### 14.2 配置升级

在升级前检查新版本的配置文件格式是否有变化，并相应更新配置文件。