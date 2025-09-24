# 监控系统性能调优指南

## 1. 概述

本文档详细说明了如何对 OpenServerHub 监控系统进行性能调优，包括 Prometheus、AlertManager、Grafana 和 IPMI Exporter 的优化方法。

## 2. 性能监控指标

### 2.1 关键性能指标 (KPIs)

#### 2.1.1 数据采集性能
- **采集延迟**: <60秒
- **采集成功率**: >99%
- **并发采集能力**: 支持100+服务器同时采集

#### 2.1.2 查询性能
- **简单查询响应时间**: <100ms
- **复杂查询响应时间**: <500ms
- **范围查询响应时间**: <1秒
- **并发查询能力**: 1000 QPS

#### 2.1.3 资源使用
- **Prometheus CPU使用率**: <50%
- **Prometheus 内存使用**: <4GB
- **AlertManager CPU使用率**: <20%
- **AlertManager 内存使用**: <1GB
- **Grafana CPU使用率**: <30%
- **Grafana 内存使用**: <2GB
- **IPMI Exporter CPU使用率**: <10% (每个实例)
- **IPMI Exporter 内存使用**: <100MB (每个实例)

### 2.2 容量规划
- **每台服务器指标数**: ~100个
- **总指标数(200台)**: ~20,000个
- **数据点频率**: 每分钟
- **存储增长**: ~1GB/月

## 3. Prometheus 性能优化

### 3.1 配置优化

#### 3.1.1 抓取间隔调整
```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 60s     # 从30s调整到60s
  evaluation_interval: 60s # 从30s调整到60s
```

#### 3.1.2 存储优化
```yaml
# docker-compose.monitoring.yml
command:
  - '--storage.tsdb.retention.time=90d'      # 数据保留时间
  - '--storage.tsdb.retention.size=50GB'     # 存储大小限制
  - '--storage.tsdb.wal-compression'         # WAL压缩
```

#### 3.1.3 查询优化
```yaml
# monitoring/prometheus/prometheus.yml
global:
  query timeout: 2m        # 查询超时时间
  query max concurrency: 20 # 最大并发查询数
```

### 3.2 资源限制
```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    mem_limit: 4g
    mem_reservation: 2g
    cpus: 2.0
    cpuset: "0,1"  # 绑定到特定CPU核心
```

### 3.3 数据分片
对于大规模部署，考虑使用 Prometheus 联邦或 Thanos 进行数据分片：

```yaml
# 主Prometheus配置
scrape_configs:
  - job_name: 'federate'
    scrape_interval: 15s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job=~"ipmi-servers"}'
    static_configs:
      - targets:
        - 'prometheus-shard1:9090'
        - 'prometheus-shard2:9090'
```

### 3.4 查询优化技巧

#### 3.4.1 避免高基数查询
```promql
# 不推荐 - 高基数查询
count(ipmi_temperature_celsius)

# 推荐 - 添加标签过滤
count(ipmi_temperature_celsius{job="ipmi-servers"})
```

#### 3.4.2 使用记录规则
```yaml
# monitoring/prometheus/rules/recording_rules.yml
groups:
  - name: hardware_stats
    interval: 5m
    rules:
      - record: job:ipmi_temperature_avg:avg
        expr: avg by(job) (ipmi_temperature_celsius)
```

## 4. AlertManager 性能优化

### 4.1 配置优化

#### 4.1.1 告警分组优化
```yaml
# monitoring/alertmanager/alertmanager.yml
route:
  group_by: ['alertname', 'cluster']
  group_wait: 30s     # 从10s增加到30s
  group_interval: 5m  # 从10s增加到5m
  repeat_interval: 4h # 从12h减少到4h
```

#### 4.1.2 抑制规则
```yaml
# monitoring/alertmanager/alertmanager.yml
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['server_name', 'cluster']
```

### 4.2 资源限制
```yaml
# docker-compose.monitoring.yml
services:
  alertmanager:
    mem_limit: 1g
    mem_reservation: 500m
    cpus: 1.0
```

## 5. Grafana 性能优化

### 5.1 面板优化

#### 5.1.1 查询优化
```json
{
  "targets": [
    {
      "expr": "rate(ipmi_fan_speed_rpm[5m])",
      "interval": "60s",  // 设置查询间隔
      "legendFormat": "{{server_name}}"
    }
  ]
}
```

#### 5.1.2 面板刷新间隔
```json
{
  "refresh": "30s"  // 设置面板刷新间隔
}
```

### 5.2 数据源优化
```yaml
# monitoring/grafana/provisioning/datasources/prometheus.yml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    jsonData:
      timeInterval: "60s"  # 设置时间间隔
      queryTimeout: "60s"  # 设置查询超时
```

### 5.3 资源限制
```yaml
# docker-compose.monitoring.yml
services:
  grafana:
    mem_limit: 2g
    mem_reservation: 1g
    cpus: 1.5
```

## 6. IPMI Exporter 性能优化

### 6.1 配置优化

#### 6.1.1 超时设置
```yaml
# monitoring/ipmi-exporter/ipmi_local.yml
modules:
  default:
    collectors:
    - ipmi
    ipmi:
      timeout: 30000  # 30秒超时
```

#### 6.1.2 传感器过滤
```yaml
# monitoring/ipmi-exporter/ipmi_local.yml
modules:
  default:
    collectors:
    - ipmi
    exclude_sensor_ids:
    - 2  # 排除不必要的传感器
    - 5
```

### 6.2 资源限制
```yaml
# docker-compose.monitoring.yml
services:
  ipmi-exporter:
    mem_limit: 128m
    mem_reservation: 64m
    cpus: 0.5
```

## 7. 网络优化

### 7.1 网络配置
```yaml
# docker-compose.monitoring.yml
networks:
  monitoring:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: 1500
```

### 7.2 连接池优化
```yaml
# monitoring/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'ipmi-servers'
    scrape_interval: 60s
    scrape_timeout: 30s  # 设置抓取超时
```

## 8. 存储优化

### 8.1 Prometheus 存储优化
```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    volumes:
      - type: volume
        source: prometheus_data
        target: /prometheus
        volume:
          nocopy: true
    tmpfs:
      - /prometheus/wal  # 使用tmpfs存储WAL
```

### 8.2 数据保留策略
```yaml
# docker-compose.monitoring.yml
command:
  - '--storage.tsdb.retention.time=90d'
  - '--storage.tsdb.retention.size=50GB'
```

## 9. 监控和告警

### 9.1 系统健康监控
```yaml
# monitoring/prometheus/rules/system_health.yml
groups:
  - name: system_health
    rules:
      - alert: PrometheusHighCPU
        expr: rate(process_cpu_seconds_total[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Prometheus CPU使用率过高"

      - alert: PrometheusHighMemory
        expr: process_resident_memory_bytes > 4e9  # 4GB
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Prometheus内存使用过高"
```

### 9.2 性能监控面板
在 Grafana 中创建专门的性能监控仪表板，包含以下指标：
- CPU和内存使用率
- 磁盘I/O
- 网络流量
- Prometheus查询性能
- AlertManager处理延迟

## 10. 压力测试

### 10.1 测试工具
使用以下工具进行压力测试：
- **Prometheus Benchmark**: 测试Prometheus查询性能
- **Apache Bench (ab)**: 测试API响应时间
- **JMeter**: 测试并发查询能力

### 10.2 测试场景
1. **高并发查询测试**: 模拟1000个并发查询
2. **大数据量查询测试**: 查询90天历史数据
3. **高频率采集测试**: 每10秒采集一次数据
4. **故障恢复测试**: 模拟组件故障和恢复

## 11. 性能调优检查清单

### 11.1 配置检查
- [ ] Prometheus抓取间隔是否合理
- [ ] AlertManager分组策略是否优化
- [ ] Grafana面板刷新间隔是否合适
- [ ] IPMI Exporter超时设置是否合理

### 11.2 资源检查
- [ ] 各组件CPU和内存限制是否设置
- [ ] 磁盘空间是否充足
- [ ] 网络带宽是否足够

### 11.3 查询检查
- [ ] 是否避免了高基数查询
- [ ] 是否使用了记录规则
- [ ] 查询超时设置是否合理

### 11.4 存储检查
- [ ] 数据保留策略是否合理
- [ ] 存储压缩是否启用
- [ ] 定期清理策略是否实施

## 12. 最佳实践

### 12.1 部署最佳实践
1. 使用SSD存储Prometheus数据
2. 为各组件设置资源限制
3. 实施数据备份策略
4. 定期监控系统健康状态

### 12.2 查询最佳实践
1. 避免使用过于复杂的查询表达式
2. 合理使用记录规则预计算
3. 添加适当的标签过滤
4. 限制查询时间范围

### 12.3 运维最佳实践
1. 定期审查和优化配置
2. 监控性能指标变化
3. 实施自动化运维脚本
4. 建立性能问题响应流程

## 13. 故障排除

### 13.1 性能问题诊断
1. **CPU使用率过高**
   - 检查查询复杂度
   - 检查抓取目标数量
   - 检查告警规则复杂度

2. **内存使用过高**
   - 检查时间序列数量
   - 检查标签基数
   - 检查数据保留时间

3. **磁盘I/O过高**
   - 检查WAL写入频率
   - 检查数据压缩设置
   - 检查查询负载

### 13.2 常用诊断命令
```bash
# 查看Prometheus指标
curl http://localhost:9090/metrics

# 查看Prometheus配置
curl http://localhost:9090/api/v1/status/config

# 查看Prometheus目标状态
curl http://localhost:9090/api/v1/targets

# 查看Prometheus规则状态
curl http://localhost:9090/api/v1/rules
```

## 14. 附录

### 14.1 性能测试脚本示例
```bash
#!/bin/bash
# Prometheus查询性能测试脚本

PROMETHEUS_URL="http://localhost:9090"
QUERIES=(
  "up"
  "ipmi_temperature_celsius"
  "rate(ipmi_fan_speed_rpm[5m])"
)

for query in "${QUERIES[@]}"; do
  echo "Testing query: $query"
  time curl -s "$PROMETHEUS_URL/api/v1/query?query=$query" > /dev/null
  echo ""
done
```

### 14.2 性能监控面板JSON
```json
{
  "dashboard": {
    "title": "监控系统性能监控",
    "panels": [
      {
        "title": "Prometheus CPU使用率",
        "type": "timeseries",
        "targets": [
          {
            "expr": "rate(process_cpu_seconds_total[5m])",
            "legendFormat": "CPU使用率"
          }
        ]
      }
    ]
  }
}
```

### 14.3 性能调优配置模板
```yaml
# prometheus-performance-optimized.yml
global:
  scrape_interval: 60s
  evaluation_interval: 60s
  query_timeout: 2m

scrape_configs:
  - job_name: 'ipmi-servers'
    scrape_interval: 60s
    scrape_timeout: 30s
    metrics_path: /metrics
    file_sd_configs:
      - files:
        - '/etc/prometheus/targets/ipmi-targets.json'
```