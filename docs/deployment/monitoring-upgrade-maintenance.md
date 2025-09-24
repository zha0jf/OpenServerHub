# 监控系统升级和维护指南

## 1. 概述

本文档详细说明了 OpenServerHub 监控系统的升级和维护流程，包括版本升级、日常维护、性能优化等内容，确保监控系统的稳定运行和持续改进。

## 2. 版本升级

### 2.1 升级策略

#### 2.1.1 版本兼容性
- 主版本升级：可能包含不兼容的变更，需要详细测试
- 次版本升级：新增功能，向后兼容
- 修订版本升级：错误修复，向后兼容

#### 2.1.2 升级计划
```bash
# 升级前准备
1. 备份当前配置和数据
2. 检查版本兼容性
3. 制定回滚计划
4. 通知相关用户
```

### 2.2 Prometheus 升级

#### 2.2.1 升级步骤
```bash
# 1. 备份配置和数据
docker run --rm \
  -v prometheus_data:/prometheus \
  -v /backup/path:/backup \
  busybox tar czf /backup/prometheus_backup_$(date +%Y%m%d).tar.gz -C /prometheus .

# 2. 拉取新版本镜像
docker-compose -f docker-compose.monitoring.yml pull prometheus

# 3. 停止当前服务
docker-compose -f docker-compose.monitoring.yml stop prometheus

# 4. 启动新版本服务
docker-compose -f docker-compose.monitoring.yml up -d prometheus

# 5. 验证升级结果
docker logs prometheus
curl http://localhost:9090/status
```

#### 2.2.2 配置迁移
```bash
# 检查新版本配置变更
# 1. 查看版本发布说明
# 2. 对比配置文件差异
# 3. 更新配置文件
# 4. 验证配置有效性
promtool check config monitoring/prometheus/prometheus.yml
```

### 2.3 AlertManager 升级

#### 2.3.1 升级步骤
```bash
# 1. 备份配置文件
cp monitoring/alertmanager/alertmanager.yml monitoring/alertmanager/alertmanager.yml.backup

# 2. 拉取新版本镜像
docker-compose -f docker-compose.monitoring.yml pull alertmanager

# 3. 停止当前服务
docker-compose -f docker-compose.monitoring.yml stop alertmanager

# 4. 启动新版本服务
docker-compose -f docker-compose.monitoring.yml up -d alertmanager

# 5. 验证升级结果
docker logs alertmanager
curl http://localhost:9093/status
```

#### 2.3.2 配置验证
```yaml
# 检查配置文件兼容性
# 1. 使用新版本工具验证配置
docker run --rm -v $(pwd)/monitoring/alertmanager:/config \
  prom/alertmanager:v0.26.0 --config.file=/config/alertmanager.yml --dry-run
```

### 2.4 Grafana 升级

#### 2.4.1 升级步骤
```bash
# 1. 备份数据和配置
docker run --rm \
  -v grafana_data:/var/lib/grafana \
  -v /backup/path:/backup \
  busybox tar czf /backup/grafana_backup_$(date +%Y%m%d).tar.gz -C /var/lib/grafana .

# 2. 拉取新版本镜像
docker-compose -f docker-compose.monitoring.yml pull grafana

# 3. 停止当前服务
docker-compose -f docker-compose.monitoring.yml stop grafana

# 4. 启动新版本服务
docker-compose -f docker-compose.monitoring.yml up -d grafana

# 5. 验证升级结果
docker logs grafana
curl http://localhost:3001/api/health
```

#### 2.4.2 插件兼容性
```bash
# 检查插件兼容性
# 1. 查看插件兼容性列表
# 2. 更新不兼容的插件
# 3. 验证插件功能
```

### 2.5 IPMI Exporter 升级

#### 2.5.1 批量升级
```bash
# 1. 备份配置文件
cp monitoring/ipmi-exporter/ipmi_local.yml monitoring/ipmi-exporter/ipmi_local.yml.backup

# 2. 拉取新版本镜像
docker-compose -f docker-compose.monitoring.yml pull ipmi-exporter

# 3. 重启所有 IPMI Exporter
docker-compose -f docker-compose.monitoring.yml up -d --force-recreate ipmi-exporter

# 4. 验证升级结果
docker logs ipmi-exporter-1
```

#### 2.5.2 逐个升级
```bash
# 对于大量服务器，可以逐个升级
# 1. 停止单个 Exporter
docker stop ipmi-exporter-1

# 2. 启动新版本 Exporter
docker run -d \
  --name ipmi-exporter-1 \
  --restart unless-stopped \
  -p 9290:9290 \
  -v $(pwd)/monitoring/ipmi-exporter/ipmi_local.yml:/config/ipmi_local.yml \
  prometheuscommunity/ipmi-exporter:v1.4.0 \
  --config.file=/config/ipmi_local.yml

# 3. 验证升级结果
docker logs ipmi-exporter-1
```

## 3. 日常维护

### 3.1 数据清理

#### 3.1.1 自动清理
```yaml
# Prometheus 自动数据清理配置
# docker-compose.monitoring.yml
command:
  - '--storage.tsdb.retention.time=90d'  # 保留90天数据
```

#### 3.1.2 手动清理
```bash
# 清理过期的监控数据
# 1. 停止 Prometheus 服务
docker-compose -f docker-compose.monitoring.yml stop prometheus

# 2. 删除旧数据文件
# 注意：此操作不可逆，请确保已备份重要数据
docker run --rm -v prometheus_data:/prometheus \
  busybox find /prometheus -name "*.db" -mtime +90 -delete

# 3. 启动 Prometheus 服务
docker-compose -f docker-compose.monitoring.yml start prometheus
```

### 3.2 日志管理

#### 3.2.1 日志轮转
```yaml
# 配置日志轮转
# docker-compose.monitoring.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

#### 3.2.2 日志清理
```bash
# 清理旧日志文件
# Docker 会自动处理日志轮转，但可以手动清理
docker system prune -f
```

### 3.3 性能监控

#### 3.3.1 资源使用监控
```bash
# 监控各组件资源使用情况
docker stats prometheus alertmanager grafana

# 监控磁盘使用情况
df -h
du -sh /var/lib/docker/volumes/prometheus_data
```

#### 3.3.2 性能基准测试
```bash
# 定期进行性能基准测试
# 1. 记录当前性能指标
curl http://localhost:9090/api/v1/status/buildinfo

# 2. 执行查询性能测试
curl "http://localhost:9090/api/v1/query?query=up"

# 3. 记录测试结果用于对比
```

### 3.4 健康检查

#### 3.4.1 自动健康检查
```yaml
# 配置健康检查
# docker-compose.monitoring.yml
healthcheck:
  test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
  interval: 30s
  timeout: 10s
  retries: 3
```

#### 3.4.2 手动健康检查
```bash
# 手动检查各组件健康状态
# Prometheus 健康检查
curl -s http://localhost:9090/-/healthy | grep "Prometheus is Healthy"

# AlertManager 健康检查
curl -s http://localhost:9093/-/healthy | grep "AlertManager is Healthy"

# Grafana 健康检查
curl -s http://localhost:3001/api/health | grep "ok"
```

## 4. 性能优化

### 4.1 查询优化

#### 4.1.1 优化查询表达式
```promql
# 避免低效的查询表达式
# 不好的查询
rate(ipmi_temperature_celsius[1y])  # 时间范围过大

# 好的查询
rate(ipmi_temperature_celsius[5m])  # 合理的时间范围

# 使用标签过滤减少数据量
ipmi_temperature_celsius{job="ipmi-servers", name=~"CPU.*"}
```

#### 4.1.2 缓存优化
```python
# 实现查询结果缓存
from redis import Redis

redis_client = Redis(host='localhost', port=6379, db=0)

def cached_query(query, time_range):
    cache_key = f"query:{query}:{time_range}"
    cached_result = redis_client.get(cache_key)
    
    if cached_result:
        return json.loads(cached_result)
    
    # 执行实际查询
    result = execute_prometheus_query(query, time_range)
    
    # 缓存结果（5分钟）
    redis_client.setex(cache_key, 300, json.dumps(result))
    
    return result
```

### 4.2 存储优化

#### 4.2.1 数据压缩
```yaml
# Prometheus 存储优化配置
command:
  - '--storage.tsdb.retention.time=90d'
  - '--storage.tsdb.wal-compression'  # 启用 WAL 压缩
```

#### 4.2.2 分片存储
```yaml
# 对于大规模监控，考虑使用分片存储
# 配置多个 Prometheus 实例，每个实例监控部分服务器
scrape_configs:
  - job_name: 'ipmi-servers-shard-1'
    file_sd_configs:
      - files:
        - '/etc/prometheus/targets/ipmi-targets-shard-1.json'
```

### 4.3 网络优化

#### 4.3.1 网络配置优化
```yaml
# 优化 Docker 网络配置
networks:
  monitoring:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: "1454"  # 设置 MTU
```

#### 4.3.2 连接池优化
```yaml
# 优化 HTTP 连接
# Prometheus 配置
global:
  scrape_timeout: 30s  # 合理设置超时时间
  scrape_interval: 60s  # 合理设置采集间隔
```

## 5. 安全维护

### 5.1 认证和授权

#### 5.1.1 定期轮换密钥
```bash
# 轮换 Grafana API Key
# 1. 生成新的 API Key
# 2. 更新配置文件
# 3. 重启相关服务
# 4. 验证新密钥有效性
```

#### 5.1.2 用户权限审查
```bash
# 定期审查用户权限
# 1. 检查用户访问日志
# 2. 验证权限分配合理性
# 3. 更新过期或不必要的权限
```

### 5.2 安全更新

#### 5.2.1 定期更新基础镜像
```bash
# 更新基础镜像
docker-compose -f docker-compose.monitoring.yml pull
docker-compose -f docker-compose.monitoring.yml up -d
```

#### 5.2.2 漏洞扫描
```bash
# 使用安全扫描工具检查镜像漏洞
docker scan prom/prometheus:v2.47.0
docker scan prom/alertmanager:v0.26.0
docker scan grafana/grafana-enterprise:10.1.0
```

### 5.3 网络安全

#### 5.3.1 防火墙配置
```bash
# 配置防火墙规则
# 1. 限制外部访问监控端口
sudo ufw deny 9090
sudo ufw deny 9093
sudo ufw deny 3001

# 2. 只允许必要 IP 访问
sudo ufw allow from 192.168.1.0/24 to any port 9090
```

#### 5.3.2 TLS 配置
```yaml
# 配置 HTTPS 访问
# 使用反向代理（如 Nginx）为监控组件提供 HTTPS 访问
```

## 6. 备份和恢复

### 6.1 备份策略

#### 6.1.1 自动备份
```bash
# 创建备份脚本
#!/bin/bash
# backup_monitoring.sh

# 备份 Prometheus 数据
docker run --rm \
  -v prometheus_data:/prometheus \
  -v /backup/path:/backup \
  busybox tar czf /backup/prometheus_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /prometheus .

# 备份 Grafana 数据
docker run --rm \
  -v grafana_data:/var/lib/grafana \
  -v /backup/path:/backup \
  busybox tar czf /backup/grafana_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /var/lib/grafana .

# 备份配置文件
tar czf /backup/monitoring_config_$(date +%Y%m%d_%H%M%S).tar.gz monitoring/
```

#### 6.1.2 备份调度
```bash
# 配置定时备份
# crontab -e
0 2 * * * /path/to/backup_monitoring.sh  # 每天凌晨2点执行备份
```

### 6.2 恢复流程

#### 6.2.1 数据恢复
```bash
# 恢复 Prometheus 数据
# 1. 停止 Prometheus 服务
docker-compose -f docker-compose.monitoring.yml stop prometheus

# 2. 删除现有数据（谨慎操作）
docker volume rm prometheus_data

# 3. 创建新的数据卷
docker volume create prometheus_data

# 4. 恢复备份数据
docker run --rm \
  -v prometheus_data:/prometheus \
  -v /backup/path:/backup \
  busybox tar xzf /backup/prometheus_backup_20231201_103000.tar.gz -C /prometheus

# 5. 启动 Prometheus 服务
docker-compose -f docker-compose.monitoring.yml start prometheus
```

#### 6.2.2 配置恢复
```bash
# 恢复配置文件
# 1. 停止相关服务
docker-compose -f docker-compose.monitoring.yml stop

# 2. 恢复配置文件
tar xzf /backup/monitoring_config_20231201_103000.tar.gz -C .

# 3. 启动服务
docker-compose -f docker-compose.monitoring.yml up -d
```

## 7. 监控系统自监控

### 7.1 系统健康监控

#### 7.1.1 自监控指标
```yaml
# 监控监控系统本身的健康状态
# Prometheus 自监控指标
- process_cpu_seconds_total
- process_resident_memory_bytes
- prometheus_tsdb_head_series
- prometheus_tsdb_head_chunks
```

#### 7.1.2 告警规则
```yaml
# 监控系统自身健康状态的告警规则
groups:
  - name: monitoring_system
    rules:
      # Prometheus 内存使用过高
      - alert: PrometheusMemoryHigh
        expr: process_resident_memory_bytes{job="prometheus"} > 2147483648  # 2GB
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Prometheus 内存使用过高"

      # Prometheus 磁盘空间不足
      - alert: PrometheusDiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/prometheus"} / node_filesystem_size_bytes{mountpoint="/prometheus"}) < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Prometheus 磁盘空间不足"
```

### 7.2 性能监控

#### 7.2.1 查询性能监控
```yaml
# 监控查询性能
- prometheus_engine_queries
- prometheus_engine_query_duration_seconds
- prometheus_tsdb_compaction_duration_seconds
```

#### 7.2.2 采集性能监控
```yaml
# 监控数据采集性能
- prometheus_target_interval_length_seconds
- prometheus_target_scrape_pool_sync_total
- up{job="prometheus"}  # Prometheus 自身的健康状态
```

## 8. 文档和知识管理

### 8.1 文档更新

#### 8.1.1 版本更新记录
```markdown
# 版本更新记录

## v1.2.0 (2023-12-01)
### 新增功能
- 支持新的硬件传感器类型
- 增加自定义告警规则功能

### 修复问题
- 修复了温度数据采集异常的问题
- 优化了查询性能

### 已知问题
- 在特定网络环境下可能出现连接超时
```

#### 8.1.2 配置变更记录
```markdown
# 配置变更记录

## 2023-12-01
- 修改了 Prometheus 的采集间隔从30秒调整为60秒
- 更新了 AlertManager 的通知策略
- 增加了新的告警规则
```

### 8.2 知识库维护

#### 8.2.1 问题解决方案
```markdown
# 常见问题解决方案

## 问题: Prometheus 内存使用过高
### 现象
Prometheus 容器内存使用持续增长，最终导致 OOM。

### 原因
数据保留时间过长，时间序列过多。

### 解决方案
1. 调整数据保留时间
2. 优化查询表达式
3. 增加容器内存限制
```

#### 8.2.2 最佳实践
```markdown
# 监控系统最佳实践

## 查询优化
- 避免使用过大的时间范围
- 合理使用标签过滤
- 使用缓存减少重复查询
```

## 9. 总结

通过遵循本指南中的升级和维护流程，可以确保 OpenServerHub 监控系统的稳定运行和持续改进。关键是要建立完善的维护计划，定期进行系统检查和优化，并保持文档的及时更新。