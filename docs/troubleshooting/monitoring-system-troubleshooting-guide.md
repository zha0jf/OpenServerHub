# 监控系统故障排除指南

## 1. 概述

本文档提供了 OpenServerHub 监控系统常见问题的诊断和解决方法，帮助系统管理员快速定位和解决监控系统故障。

## 2. 常见问题分类

### 2.1 数据采集问题
- Prometheus 无法从 IPMI Exporter 获取数据
- IPMI Exporter 无法连接服务器 BMC
- 监控数据不完整或缺失

### 2.2 告警问题
- 告警未触发
- 告警重复发送
- 告警通知未送达

### 2.3 可视化问题
- Grafana 无法显示数据
- 仪表板加载缓慢
- 图表显示异常

### 2.4 系统性能问题
- 组件响应缓慢
- 内存或CPU使用率过高
- 磁盘空间不足

## 3. 数据采集问题排查

### 3.1 Prometheus 无法抓取数据

#### 3.1.1 检查目标状态
```bash
# 查看 Prometheus 目标状态
curl -s http://localhost:9090/api/v1/targets | jq '.'

# 检查特定目标状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.server_name=="server-01")'
```

#### 3.1.2 检查网络连接
```bash
# 测试网络连通性
ping 192.168.1.100

# 测试端口连通性
telnet 192.168.1.100 9290

# 测试 IPMI 连接
ipmitool -I lanplus -H 192.168.1.100 -U admin -P password chassis status
```

#### 3.1.3 检查配置文件
```bash
# 验证目标配置文件
cat monitoring/prometheus/targets/ipmi-targets.json

# 验证 Prometheus 配置
docker-compose -f docker-compose.monitoring.yml exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

#### 3.1.4 解决方案
```yaml
# 检查 targets 配置是否正确
[
  {
    "targets": ["192.168.1.100:9290"],
    "labels": {
      "server_id": "1",
      "server_name": "server-01",
      "ipmi_ip": "192.168.1.100"
    }
  }
]
```

### 3.2 IPMI Exporter 连接问题

#### 3.2.1 检查 Exporter 状态
```bash
# 查看 Exporter 日志
docker-compose -f docker-compose.ipmi.yml logs ipmi-exporter-1

# 检查 Exporter 运行状态
docker-compose -f docker-compose.ipmi.yml ps
```

#### 3.2.2 测试 IPMI 连接
```bash
# 在 Exporter 容器内测试 IPMI 连接
docker-compose -f docker-compose.ipmi.yml exec ipmi-exporter-1 \
  ipmitool -I lanplus -H 192.168.1.100 -U admin -P password chassis status
```

#### 3.2.3 检查配置
```yaml
# monitoring/ipmi-exporter/ipmi_local.yml
modules:
  default:
    collectors:
    - bmc
    - ipmi
    - dcmi
    - chassis
    exclude_sensor_ids:
    - 2    # 排除特定传感器
```

### 3.3 监控数据缺失

#### 3.3.1 检查时间序列
```bash
# 查询特定指标是否存在
curl -g 'http://localhost:9090/api/v1/series?match[]=ipmi_temperature_celsius{server_name="server-01"}'

# 查询最近的数据点
curl -g 'http://localhost:9090/api/v1/query?query=ipmi_temperature_celsius{server_name="server-01"}'
```

#### 3.3.2 检查抓取间隔
```yaml
# monitoring/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'ipmi-servers'
    scrape_interval: 60s  # 确保间隔合理
    scrape_timeout: 30s
```

## 4. 告警问题排查

### 4.1 告警未触发

#### 4.1.1 检查告警规则
```bash
# 查看告警规则状态
curl -s http://localhost:9090/api/v1/rules | jq '.'

# 验证告警规则
docker-compose -f docker-compose.monitoring.yml exec prometheus promtool check rules /etc/prometheus/rules/hardware_alerts.yml
```

#### 4.1.2 测试告警表达式
```bash
# 测试告警表达式
curl -g 'http://localhost:9090/api/v1/query?query=ipmi_temperature_celsius > 80'
```

#### 4.1.3 检查 AlertManager 配置
```bash
# 验证 AlertManager 配置
docker-compose -f docker-compose.monitoring.yml exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

# 查看告警状态
curl -s http://localhost:9090/api/v1/alerts | jq '.'
```

### 4.2 告警重复发送

#### 4.2.1 检查分组配置
```yaml
# monitoring/alertmanager/alertmanager.yml
route:
  group_by: ['alertname', 'cluster', 'server_name']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### 4.2.2 检查抑制规则
```yaml
# monitoring/alertmanager/alertmanager.yml
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['server_name', 'cluster']
```

### 4.3 告警通知未送达

#### 4.3.1 检查通知配置
```yaml
# monitoring/alertmanager/alertmanager.yml
receivers:
  - name: 'default'
    email_configs:
      - to: 'admin@openshub.com'
        smarthost: 'smtp.gmail.com:587'
        from: 'alerts@openshub.com'
        auth_username: 'alerts@openshub.com'
        auth_password: 'your-app-password'
```

#### 4.3.2 测试邮件发送
```bash
# 使用 amtool 测试告警发送
docker-compose -f docker-compose.monitoring.yml exec alertmanager amtool alert add alertname=Test severity=warning
```

## 5. 可视化问题排查

### 5.1 Grafana 无法显示数据

#### 5.1.1 检查数据源配置
```bash
# 查看数据源状态
curl -s -H "Authorization: Bearer YOUR_API_KEY" http://localhost:3001/api/datasources

# 测试数据源连接
curl -s -H "Authorization: Bearer YOUR_API_KEY" http://localhost:3001/api/datasources/1/health
```

#### 5.1.2 检查查询语句
```json
{
  "targets": [
    {
      "expr": "ipmi_temperature_celsius{server_name=\"server-01\"}",
      "format": "time_series"
    }
  ]
}
```

### 5.2 仪表板加载缓慢

#### 5.2.1 优化查询
```json
{
  "targets": [
    {
      "expr": "rate(ipmi_fan_speed_rpm[5m])",
      "interval": "60s",  // 增加查询间隔
      "legendFormat": "{{server_name}}"
    }
  ]
}
```

#### 5.2.2 检查面板刷新间隔
```json
{
  "refresh": "30s"  // 调整刷新间隔
}
```

### 5.3 图表显示异常

#### 5.3.1 检查单位配置
```json
{
  "fieldConfig": {
    "defaults": {
      "unit": "celsius",
      "min": 0,
      "max": 100
    }
  }
}
```

#### 5.3.2 检查时间范围
```json
{
  "timeFrom": "now-24h",  // 确保时间范围合理
  "timeShift": null
}
```

## 6. 系统性能问题排查

### 6.1 组件响应缓慢

#### 6.1.1 检查资源使用
```bash
# 查看容器资源使用情况
docker stats prometheus alertmanager grafana

# 查看系统资源使用
top
htop
iotop
```

#### 6.1.2 检查日志
```bash
# 查看 Prometheus 日志
docker-compose -f docker-compose.monitoring.yml logs -f prometheus

# 查看 AlertManager 日志
docker-compose -f docker-compose.monitoring.yml logs -f alertmanager

# 查看 Grafana 日志
docker-compose -f docker-compose.monitoring.yml logs -f grafana
```

### 6.2 内存或CPU使用率过高

#### 6.2.1 设置资源限制
```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    mem_limit: 4g
    mem_reservation: 2g
    cpus: 2.0
    cpuset: "0,1"
```

#### 6.2.2 优化配置
```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 60s  # 增加抓取间隔
  evaluation_interval: 60s
```

### 6.3 磁盘空间不足

#### 6.3.1 检查磁盘使用
```bash
# 查看磁盘使用情况
df -h

# 查看 Prometheus 数据目录大小
du -sh /var/lib/docker/volumes/prometheus_data/
```

#### 6.3.2 调整数据保留
```yaml
# docker-compose.monitoring.yml
command:
  - '--storage.tsdb.retention.time=60d'  # 减少数据保留时间
  - '--storage.tsdb.retention.size=30GB'  # 限制存储大小
```

## 7. 日志分析

### 7.1 Prometheus 日志分析
```bash
# 查看错误日志
docker-compose -f docker-compose.monitoring.yml logs prometheus | grep -i error

# 查看警告日志
docker-compose -f docker-compose.monitoring.yml logs prometheus | grep -i warn

# 查看抓取失败日志
docker-compose -f docker-compose.monitoring.yml logs prometheus | grep -i "scrape failed"
```

### 7.2 AlertManager 日志分析
```bash
# 查看通知失败日志
docker-compose -f docker-compose.monitoring.yml logs alertmanager | grep -i "notify failed"

# 查看告警处理日志
docker-compose -f docker-compose.monitoring.yml logs alertmanager | grep -i "alert received"
```

### 7.3 Grafana 日志分析
```bash
# 查看面板加载错误
docker-compose -f docker-compose.monitoring.yml logs grafana | grep -i "panel error"

# 查看数据源错误
docker-compose -f docker-compose.monitoring.yml logs grafana | grep -i "data source error"
```

## 8. 网络问题排查

### 8.1 网络连通性检查
```bash
# 检查容器间网络连通性
docker-compose -f docker-compose.monitoring.yml exec prometheus ping alertmanager

# 检查端口连通性
docker-compose -f docker-compose.monitoring.yml exec prometheus nc -zv alertmanager 9093
```

### 8.2 DNS 解析问题
```bash
# 检查 DNS 解析
docker-compose -f docker-compose.monitoring.yml exec prometheus nslookup alertmanager

# 检查 /etc/hosts 配置
docker-compose -f docker-compose.monitoring.yml exec prometheus cat /etc/hosts
```

## 9. 安全问题排查

### 9.1 认证问题
```bash
# 检查 API 访问权限
curl -H "Authorization: Bearer INVALID_TOKEN" http://localhost:9090/api/v1/query?query=up

# 检查 Grafana API Key
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:3001/api/org
```

### 9.2 网络安全
```bash
# 检查端口暴露
netstat -tlnp | grep 9090
netstat -tlnp | grep 9093
netstat -tlnp | grep 3001

# 检查防火墙规则
iptables -L
```

## 10. 性能优化建议

### 10.1 查询优化
```promql
# 避免高基数查询
# 不推荐
count(ipmi_temperature_celsius)

# 推荐
count(ipmi_temperature_celsius{job="ipmi-servers"})
```

### 10.2 使用记录规则
```yaml
# monitoring/prometheus/rules/recording_rules.yml
groups:
  - name: hardware_stats
    interval: 5m
    rules:
      - record: job:ipmi_temperature_avg:avg
        expr: avg by(job) (ipmi_temperature_celsius)
```

### 10.3 面板优化
```json
{
  "targets": [
    {
      "expr": "rate(ipmi_fan_speed_rpm[5m])",
      "interval": "60s",  // 设置合适的查询间隔
      "legendFormat": "{{server_name}}"
    }
  ],
  "refresh": "30s"  // 设置合适的刷新间隔
}
```

## 11. 监控系统自监控

### 11.1 系统健康监控
```yaml
# monitoring/prometheus/rules/system_health.yml
groups:
  - name: system_health
    rules:
      - alert: PrometheusDown
        expr: up{job="prometheus"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Prometheus 服务停止运行"

      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes{job="prometheus"} > 4e9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Prometheus 内存使用过高"
```

### 11.2 性能监控
```yaml
# monitoring/prometheus/rules/performance.yml
groups:
  - name: performance
    rules:
      - alert: SlowScrapes
        expr: rate(prometheus_target_scrapes_exceeded_sample_limit_total[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "存在抓取超时的情况"
```

## 12. 故障恢复

### 12.1 数据恢复
```bash
# 从备份恢复 Prometheus 数据
docker run --rm \
  -v prometheus_data:/prometheus \
  -v /backup/path:/backup \
  busybox tar xzf /backup/prometheus_backup.tar.gz -C /prometheus
```

### 12.2 服务恢复
```bash
# 重启所有监控服务
docker-compose -f docker-compose.monitoring.yml down
docker-compose -f docker-compose.monitoring.yml up -d

# 重启特定服务
docker-compose -f docker-compose.monitoring.yml restart prometheus
```

## 13. 预防措施

### 13.1 定期维护
```bash
# 定期清理日志
docker system prune -f

# 定期备份数据
0 2 * * * /path/to/backup_script.sh
```

### 13.2 监控告警
```yaml
# 设置监控系统自监控告警
groups:
  - name: monitoring_system
    rules:
      - alert: MonitoringSystemDown
        expr: up == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "监控系统组件停止运行"
```

## 14. 附录

### 14.1 常用诊断命令
```bash
# 查看所有容器状态
docker-compose -f docker-compose.monitoring.yml ps

# 查看容器日志
docker-compose -f docker-compose.monitoring.yml logs -f <service_name>

# 进入容器调试
docker-compose -f docker-compose.monitoring.yml exec <service_name> sh

# 查看系统资源使用
docker stats
```

### 14.2 健康检查端点
```bash
# Prometheus 健康检查
curl http://localhost:9090/-/healthy

# AlertManager 健康检查
curl http://localhost:9093/-/healthy

# Grafana 健康检查
curl http://localhost:3001/api/health
```

### 14.3 性能指标查询
```bash
# Prometheus 查询性能
curl -g 'http://localhost:9090/api/v1/query?query=prometheus_engine_query_duration_seconds'

# AlertManager 处理性能
curl -g 'http://localhost:9090/api/v1/query?query=alertmanager_notification_latency_seconds'
```