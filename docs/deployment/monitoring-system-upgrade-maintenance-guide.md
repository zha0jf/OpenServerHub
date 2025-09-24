# 监控系统升级和维护指南

## 1. 概述

本文档详细说明了 OpenServerHub 监控系统的升级和维护流程，包括版本升级、配置更新、数据备份和恢复等操作。

## 2. 版本管理

### 2.1 组件版本
| 组件 | 当前版本 | 最新版本 | 升级频率 |
|------|----------|----------|----------|
| Prometheus | v2.47.0 | v2.49.1 | 每季度 |
| AlertManager | v0.26.0 | v0.27.0 | 每季度 |
| Grafana | v10.1.0 | v10.2.3 | 每月 |
| IPMI Exporter | v1.4.0 | v1.5.0 | 每半年 |

### 2.2 版本兼容性
在升级前，请检查各组件间的版本兼容性：
- Prometheus 与 AlertManager 的 API 兼容性
- Grafana 与 Prometheus 的数据源兼容性
- IPMI Exporter 与服务器 BMC 的兼容性

## 3. 升级流程

### 3.1 升级前准备

#### 3.1.1 备份配置和数据
```bash
# 备份 Prometheus 数据
docker run --rm \
  -v prometheus_data:/prometheus \
  -v /backup/path:/backup \
  busybox tar czf /backup/prometheus_backup_$(date +%Y%m%d).tar.gz -C /prometheus .

# 备份 Grafana 数据
docker run --rm \
  -v grafana_data:/var/lib/grafana \
  -v /backup/path:/backup \
  busybox tar czf /backup/grafana_backup_$(date +%Y%m%d).tar.gz -C /var/lib/grafana .

# 备份配置文件
cp -r monitoring /backup/path/monitoring_$(date +%Y%m%d)
```

#### 3.1.2 检查版本兼容性
```bash
# 检查当前版本
docker-compose -f docker-compose.monitoring.yml exec prometheus prometheus --version
docker-compose -f docker-compose.monitoring.yml exec alertmanager alertmanager --version
docker-compose -f docker-compose.monitoring.yml exec grafana grafana-server -v
```

#### 3.1.3 制定回滚计划
- 记录当前版本号
- 准备回滚脚本
- 确认备份完整性

### 3.2 Prometheus 升级

#### 3.2.1 升级步骤
```bash
# 1. 停止 Prometheus 服务
docker-compose -f docker-compose.monitoring.yml stop prometheus

# 2. 更新 Docker 镜像
docker-compose -f docker-compose.monitoring.yml pull prometheus

# 3. 启动新版本
docker-compose -f docker-compose.monitoring.yml up -d prometheus

# 4. 验证升级
docker-compose -f docker-compose.monitoring.yml exec prometheus prometheus --version
```

#### 3.2.2 配置迁移
检查新版本的配置文件变更：
```yaml
# monitoring/prometheus/prometheus.yml
# 新版本可能需要调整的配置项
global:
  # 检查是否有新的全局配置选项
rule_files:
  # 检查规则文件格式是否有变化
scrape_configs:
  # 检查抓取配置是否有新选项
```

### 3.3 AlertManager 升级

#### 3.3.1 升级步骤
```bash
# 1. 停止 AlertManager 服务
docker-compose -f docker-compose.monitoring.yml stop alertmanager

# 2. 更新 Docker 镜像
docker-compose -f docker-compose.monitoring.yml pull alertmanager

# 3. 启动新版本
docker-compose -f docker-compose.monitoring.yml up -d alertmanager

# 4. 验证升级
docker-compose -f docker-compose.monitoring.yml exec alertmanager alertmanager --version
```

#### 3.3.2 配置迁移
检查新版本的配置文件变更：
```yaml
# monitoring/alertmanager/alertmanager.yml
# 新版本可能需要调整的配置项
global:
  # 检查是否有新的全局配置选项
route:
  # 检查路由配置是否有新选项
receivers:
  # 检查接收器配置是否有新选项
```

### 3.4 Grafana 升级

#### 3.4.1 升级步骤
```bash
# 1. 停止 Grafana 服务
docker-compose -f docker-compose.monitoring.yml stop grafana

# 2. 更新 Docker 镜像
docker-compose -f docker-compose.monitoring.yml pull grafana

# 3. 启动新版本
docker-compose -f docker-compose.monitoring.yml up -d grafana

# 4. 验证升级
docker-compose -f docker-compose.monitoring.yml exec grafana grafana-server -v
```

#### 3.4.2 插件兼容性
检查插件兼容性：
```bash
# 查看已安装插件
docker-compose -f docker-compose.monitoring.yml exec grafana grafana-cli plugins ls

# 更新插件（如果需要）
docker-compose -f docker-compose.monitoring.yml exec grafana grafana-cli plugins update-all
```

### 3.5 IPMI Exporter 升级

#### 3.5.1 升级步骤
```bash
# 1. 停止所有 IPMI Exporter 实例
docker-compose -f docker-compose.ipmi.yml down

# 2. 更新 Docker 镜像
docker-compose -f docker-compose.ipmi.yml pull

# 3. 启动新版本
docker-compose -f docker-compose.ipmi.yml up -d

# 4. 验证升级
docker-compose -f docker-compose.ipmi.yml exec ipmi-exporter-1 ipmi_exporter --version
```

## 4. 配置更新

### 4.1 配置文件管理

#### 4.1.1 配置版本控制
```bash
# 使用 Git 管理配置文件
cd monitoring
git init
git add .
git commit -m "Initial configuration files"

# 定期提交配置变更
git add .
git commit -m "Update alert rules"
```

#### 4.1.2 配置文件验证
```bash
# 验证 Prometheus 配置
docker-compose -f docker-compose.monitoring.yml exec prometheus promtool check config /etc/prometheus/prometheus.yml

# 验证告警规则
docker-compose -f docker-compose.monitoring.yml exec prometheus promtool check rules /etc/prometheus/rules/hardware_alerts.yml

# 验证 AlertManager 配置
docker-compose -f docker-compose.monitoring.yml exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
```

### 4.2 动态配置更新

#### 4.2.1 Prometheus 配置重载
```bash
# 通知 Prometheus 重新加载配置
curl -X POST http://localhost:9090/-/reload

# 或使用 Docker 命令
docker-compose -f docker-compose.monitoring.yml exec prometheus kill -HUP 1
```

#### 4.2.2 AlertManager 配置重载
```bash
# 通知 AlertManager 重新加载配置
curl -X POST http://localhost:9093/-/reload

# 或使用 Docker 命令
docker-compose -f docker-compose.monitoring.yml exec alertmanager kill -HUP 1
```

## 5. 数据备份和恢复

### 5.1 定期备份策略

#### 5.1.1 备份计划
```bash
# 创建备份脚本 backup_monitoring.sh
#!/bin/bash
BACKUP_DIR="/backup/monitoring"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR/$DATE

# 备份 Prometheus 数据
docker run --rm \
  -v prometheus_data:/prometheus \
  -v $BACKUP_DIR/$DATE:/backup \
  busybox tar czf /backup/prometheus.tar.gz -C /prometheus .

# 备份 Grafana 数据
docker run --rm \
  -v grafana_data:/var/lib/grafana \
  -v $BACKUP_DIR/$DATE:/backup \
  busybox tar czf /backup/grafana.tar.gz -C /var/lib/grafana .

# 备份配置文件
cp -r monitoring $BACKUP_DIR/$DATE/config

# 清理旧备份（保留最近7天）
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} \;
```

#### 5.1.2 自动化备份
```bash
# 添加到 crontab
0 2 * * * /path/to/backup_monitoring.sh
```

### 5.2 数据恢复

#### 5.2.1 Prometheus 数据恢复
```bash
# 停止 Prometheus 服务
docker-compose -f docker-compose.monitoring.yml stop prometheus

# 恢复数据
docker run --rm \
  -v prometheus_data:/prometheus \
  -v /backup/path:/backup \
  busybox tar xzf /backup/prometheus.tar.gz -C /prometheus

# 启动 Prometheus 服务
docker-compose -f docker-compose.monitoring.yml up -d prometheus
```

#### 5.2.2 Grafana 数据恢复
```bash
# 停止 Grafana 服务
docker-compose -f docker-compose.monitoring.yml stop grafana

# 恢复数据
docker run --rm \
  -v grafana_data:/var/lib/grafana \
  -v /backup/path:/backup \
  busybox tar xzf /backup/grafana.tar.gz -C /var/lib/grafana

# 启动 Grafana 服务
docker-compose -f docker-compose.monitoring.yml up -d grafana
```

## 6. 系统维护

### 6.1 定期维护任务

#### 6.1.1 日志清理
```bash
# 清理 Docker 日志
docker system prune -f

# 清理容器日志
truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

#### 6.1.2 磁盘空间管理
```bash
# 检查磁盘使用情况
df -h

# 清理未使用的 Docker 镜像
docker image prune -a -f

# 清理未使用的卷
docker volume prune -f
```

#### 6.1.3 数据清理
```bash
# 调整 Prometheus 数据保留时间
docker-compose -f docker-compose.monitoring.yml exec prometheus \
  sed -i 's/--storage.tsdb.retention.time=90d/--storage.tsdb.retention.time=60d/' /etc/prometheus/prometheus.yml
```

### 6.2 健康检查

#### 6.2.1 组件健康检查
```bash
# 检查 Prometheus 健康状态
curl -s http://localhost:9090/-/healthy | grep "Prometheus is Healthy"

# 检查 AlertManager 健康状态
curl -s http://localhost:9093/-/healthy | grep "OK"

# 检查 Grafana 健康状态
curl -s http://localhost:3001/api/health | grep "ok"
```

#### 6.2.2 自动化健康检查
```bash
# 创建健康检查脚本 health_check.sh
#!/bin/bash
SERVICES=("prometheus" "alertmanager" "grafana")

for service in "${SERVICES[@]}"; do
  if curl -s --head http://localhost:9090/-/healthy | head -n 1 | grep "200 OK" > /dev/null; then
    echo "$service is healthy"
  else
    echo "$service is unhealthy"
    # 发送告警通知
  fi
done
```

## 7. 故障处理

### 7.1 常见故障及解决方案

#### 7.1.1 Prometheus 启动失败
```bash
# 查看日志
docker-compose -f docker-compose.monitoring.yml logs prometheus

# 检查配置文件
docker-compose -f docker-compose.monitoring.yml exec prometheus promtool check config /etc/prometheus/prometheus.yml

# 重新启动
docker-compose -f docker-compose.monitoring.yml restart prometheus
```

#### 7.1.2 AlertManager 告警不发送
```bash
# 查看日志
docker-compose -f docker-compose.monitoring.yml logs alertmanager

# 检查配置
docker-compose -f docker-compose.monitoring.yml exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

# 测试告警发送
docker-compose -f docker-compose.monitoring.yml exec alertmanager amtool alert add alertname=test severity=warning
```

#### 7.1.3 Grafana 无法访问
```bash
# 查看日志
docker-compose -f docker-compose.monitoring.yml logs grafana

# 检查端口占用
netstat -tlnp | grep 3001

# 重新启动
docker-compose -f docker-compose.monitoring.yml restart grafana
```

### 7.2 回滚操作

#### 7.2.1 回滚到旧版本
```bash
# 1. 停止当前服务
docker-compose -f docker-compose.monitoring.yml down

# 2. 恢复旧版本配置
cp /backup/path/docker-compose.monitoring.yml.old docker-compose.monitoring.yml

# 3. 启动旧版本
docker-compose -f docker-compose.monitoring.yml up -d

# 4. 验证回滚
docker-compose -f docker-compose.monitoring.yml ps
```

## 8. 安全维护

### 8.1 认证信息更新

#### 8.1.1 密码轮换
```bash
# 更新 Grafana 管理员密码
docker-compose -f docker-compose.monitoring.yml exec grafana grafana-cli admin reset-admin-password newpassword

# 更新 AlertManager SMTP 密码
# 编辑 monitoring/alertmanager/alertmanager.yml
# 重启 AlertManager 服务
docker-compose -f docker-compose.monitoring.yml restart alertmanager
```

#### 8.1.2 API Key 管理
```bash
# 创建新的 Grafana API Key
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"name":"new-key","role":"Admin"}' \
  http://localhost:3001/api/auth/keys

# 删除旧的 API Key
curl -X DELETE \
  -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:3001/api/auth/keys/KEY_ID
```

### 8.2 安全补丁应用

#### 8.2.1 系统更新
```bash
# 更新基础镜像
docker-compose -f docker-compose.monitoring.yml pull

# 重启服务应用更新
docker-compose -f docker-compose.monitoring.yml up -d
```

#### 8.2.2 漏洞扫描
```bash
# 使用 Trivy 扫描镜像漏洞
trivy image prom/prometheus:v2.47.0
trivy image prom/alertmanager:v0.26.0
trivy image grafana/grafana-enterprise:10.1.0
```

## 9. 监控和告警

### 9.1 系统监控
```yaml
# monitoring/prometheus/rules/system_monitoring.yml
groups:
  - name: system_monitoring
    rules:
      - alert: MonitoringServiceDown
        expr: up{job=~"prometheus|alertmanager|grafana"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "监控服务 {{ $labels.job }} 停止运行"

      - alert: HighDiskUsage
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "磁盘使用率过高 {{ $value }}%"
```

### 9.2 维护窗口
```yaml
# 设置维护窗口避免告警干扰
# 在 AlertManager 中配置抑制规则
inhibit_rules:
  - source_match:
      alertname: MaintenanceWindow
    target_match:
      severity: warning
    equal: ['instance']
```

## 10. 文档更新

### 10.1 版本更新记录
```markdown
## 版本更新历史

### v1.2.0 (2024-01-15)
- 升级 Prometheus 到 v2.47.0
- 升级 AlertManager 到 v0.26.0
- 升级 Grafana 到 v10.1.0
- 优化存储配置

### v1.1.0 (2023-10-01)
- 初始版本发布
- 集成 Prometheus + AlertManager + Grafana
- 实现动态配置管理
```

### 10.2 配置变更记录
```markdown
## 配置变更历史

### 2024-01-10
- 调整 Prometheus 抓取间隔从 30s 到 60s
- 增加数据保留时间从 60d 到 90d

### 2023-12-01
- 优化 AlertManager 分组策略
- 调整告警重复间隔
```

## 11. 最佳实践

### 11.1 升级最佳实践
1. 在非高峰时段进行升级
2. 提前备份所有数据和配置
3. 在测试环境中验证升级流程
4. 准备详细的回滚计划
5. 升级后进行全面的功能测试

### 11.2 维护最佳实践
1. 建立定期维护计划
2. 实施自动化监控和告警
3. 定期审查和优化配置
4. 保持文档的实时更新
5. 建立完善的故障响应流程

### 11.3 安全最佳实践
1. 定期轮换认证凭据
2. 及时应用安全补丁
3. 实施最小权限原则
4. 定期进行安全扫描
5. 监控安全事件和异常行为

## 12. 附录

### 12.1 常用命令汇总
```bash
# 备份 Prometheus 数据
docker run --rm -v prometheus_data:/prometheus -v /backup:/backup busybox tar czf /backup/prometheus.tar.gz -C /prometheus .

# 备份 Grafana 数据
docker run --rm -v grafana_data:/var/lib/grafana -v /backup:/backup busybox tar czf /backup/grafana.tar.gz -C /var/lib/grafana .

# 验证 Prometheus 配置
docker-compose -f docker-compose.monitoring.yml exec prometheus promtool check config /etc/prometheus/prometheus.yml

# 验证告警规则
docker-compose -f docker-compose.monitoring.yml exec prometheus promtool check rules /etc/prometheus/rules/hardware_alerts.yml

# 重新加载配置
curl -X POST http://localhost:9090/-/reload
```

### 12.2 检查清单
- [ ] 备份所有数据和配置
- [ ] 验证版本兼容性
- [ ] 制定回滚计划
- [ ] 在测试环境验证
- [ ] 通知相关团队
- [ ] 执行升级操作
- [ ] 验证升级结果
- [ ] 更新文档记录
- [ ] 监控系统运行状态