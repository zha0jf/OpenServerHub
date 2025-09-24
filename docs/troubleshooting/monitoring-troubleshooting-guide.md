# 监控系统故障排除指南

## 1. 概述

本文档提供了 OpenServerHub 监控系统常见问题的诊断和解决方法，帮助用户快速解决监控系统运行中遇到的问题。

## 2. 常见问题分类

### 2.1 数据采集问题
- 监控数据缺失
- 数据采集失败
- 采集频率异常

### 2.2 告警问题
- 告警未触发
- 告警误报
- 告警通知失败

### 2.3 可视化问题
- Grafana 无法显示数据
- 图表渲染异常
- 仪表板加载缓慢

### 2.4 系统性能问题
- 组件响应缓慢
- 资源使用过高
- 系统不稳定

### 2.5 配置问题
- 配置文件错误
- 权限配置问题
- 网络配置问题

## 3. 数据采集问题排查

### 3.1 监控数据缺失

#### 问题现象
- 监控仪表板显示无数据
- Prometheus 查询返回空结果
- 历史数据查询无结果

#### 诊断步骤
1. **检查 IPMI Exporter 状态**
   ```bash
   # 检查 IPMI Exporter 容器状态
   docker ps | grep ipmi-exporter
   
   # 查看 IPMI Exporter 日志
   docker logs ipmi-exporter-1
   ```

2. **检查服务器 BMC 连接**
   ```bash
   # 测试 BMC 连接
   ping 192.168.1.100
   
   # 测试 IPMI 连接
   ipmitool -H 192.168.1.100 -U admin -P password chassis status
   ```

3. **检查 Prometheus 抓取状态**
   ```bash
   # 访问 Prometheus Targets 页面
   # http://localhost:9090/targets
   
   # 检查目标状态是否为 UP
   ```

4. **检查配置文件**
   ```bash
   # 检查目标配置文件
   cat monitoring/prometheus/targets/ipmi-targets.json
   ```

#### 解决方案
1. **重启 IPMI Exporter**
   ```bash
   docker restart ipmi-exporter-1
   ```

2. **更新目标配置**
   ```bash
   # 确保目标配置文件格式正确
   # 通知 Prometheus 重新加载配置
   curl -X POST http://localhost:9090/-/reload
   ```

3. **检查 BMC 配置**
   - 验证 BMC IP 地址、用户名、密码是否正确
   - 检查 BMC 网络连接是否正常
   - 确认 BMC IPMI 功能是否启用

### 3.2 数据采集失败

#### 问题现象
- IPMI Exporter 日志显示连接错误
- Prometheus 抓取目标状态为 DOWN
- 部分指标无法采集

#### 诊断步骤
1. **查看详细错误日志**
   ```bash
   # 查看 IPMI Exporter 详细日志
   docker logs -f ipmi-exporter-1 --tail 100
   ```

2. **测试 IPMI 命令**
   ```bash
   # 测试传感器数据读取
   ipmitool -H 192.168.1.100 -U admin -P password sensor list
   ```

3. **检查网络连通性**
   ```bash
   # 检查网络延迟
   ping -c 4 192.168.1.100
   
   # 检查端口连通性
   telnet 192.168.1.100 623
   ```

#### 解决方案
1. **调整 IPMI 配置**
   ```yaml
   # monitoring/ipmi-exporter/ipmi_local.yml
   modules:
     default:
       ipmi:
         timeout: 30000  # 增加超时时间
         privilege: "user"
   ```

2. **检查防火墙设置**
   - 确保 BMC IPMI 端口（通常为 623）未被防火墙阻止
   - 检查 Docker 网络配置

3. **更新认证信息**
   - 验证 BMC 用户名和密码是否正确
   - 检查用户权限是否足够

### 3.3 采集频率异常

#### 问题现象
- 数据更新频率不符合预期
- 监控数据出现断续现象
- 采集间隔不规律

#### 诊断步骤
1. **检查 Prometheus 配置**
   ```yaml
   # monitoring/prometheus/prometheus.yml
   scrape_configs:
     - job_name: 'ipmi-servers'
       scrape_interval: 60s  # 检查采集间隔设置
   ```

2. **检查系统负载**
   ```bash
   # 检查系统资源使用情况
   docker stats prometheus
   ```

3. **查看抓取统计**
   ```bash
   # 访问 Prometheus Status -> Targets 页面
   # 检查 Last Scrape 时间
   ```

#### 解决方案
1. **调整采集频率**
   ```yaml
   # 根据系统性能调整采集频率
   scrape_configs:
     - job_name: 'ipmi-servers'
       scrape_interval: 120s  # 降低采集频率
   ```

2. **优化系统性能**
   - 增加 Prometheus 容器资源限制
   - 减少不必要的监控目标
   - 优化查询表达式

## 4. 告警问题排查

### 4.1 告警未触发

#### 问题现象
- 监控指标超过阈值但未触发告警
- AlertManager 无相关告警记录
- 告警历史查询无结果

#### 诊断步骤
1. **检查告警规则**
   ```bash
   # 查看告警规则状态
   # 访问 Prometheus Alerts 页面
   # http://localhost:9090/alerts
   ```

2. **验证表达式**
   ```promql
   # 在 Prometheus Graph 页面测试告警表达式
   ipmi_temperature_celsius > 80
   ```

3. **检查持续时间**
   ```yaml
   # 检查告警规则的持续时间设置
   - alert: HighCPUTemperature
     expr: ipmi_temperature_celsius > 80
     for: 5m  # 检查持续时间是否过长
   ```

#### 解决方案
1. **调整告警规则**
   ```yaml
   # 优化告警规则
   - alert: HighCPUTemperature
     expr: ipmi_temperature_celsius > 80
     for: 2m  # 适当缩短持续时间
     labels:
       severity: warning
   ```

2. **检查指标数据**
   - 确认监控指标名称是否正确
   - 验证指标标签是否匹配
   - 检查数据采集是否正常

### 4.2 告警误报

#### 问题现象
- 监控指标正常但触发告警
- 告警频繁触发和恢复
- 告警条件与实际不符

#### 诊断步骤
1. **分析告警数据**
   ```promql
   # 查询相关指标的历史数据
   ipmi_temperature_celsius[1h]
   ```

2. **检查告警表达式**
   ```yaml
   # 检查表达式是否过于敏感
   expr: ipmi_temperature_celsius > 80
   ```

3. **查看告警历史**
   ```bash
   # 访问 AlertManager 页面查看告警历史
   # http://localhost:9093
   ```

#### 解决方案
1. **优化告警条件**
   ```yaml
   # 增加过滤条件减少误报
   - alert: HighCPUTemperature
     expr: ipmi_temperature_celsius{name=~".*CPU.*"} > 85
     for: 5m
   ```

2. **调整阈值**
   ```yaml
   # 根据历史数据调整阈值
   - alert: HighCPUTemperature
     expr: ipmi_temperature_celsius > 90  # 提高阈值
     for: 5m
   ```

### 4.3 告警通知失败

#### 问题现象
- 告警触发但未收到通知
- 邮件发送失败
- Webhook 调用失败

#### 诊断步骤
1. **检查 AlertManager 配置**
   ```yaml
   # monitoring/alertmanager/alertmanager.yml
   global:
     smtp_smarthost: 'smtp.gmail.com:587'
     smtp_from: 'alerts@openshub.com'
   ```

2. **查看 AlertManager 日志**
   ```bash
   docker logs alertmanager
   ```

3. **测试通知配置**
   ```bash
   # 测试邮件发送
   echo "Test message" | mail -s "Test" admin@openshub.com
   ```

#### 解决方案
1. **修复 SMTP 配置**
   ```yaml
   global:
     smtp_smarthost: 'smtp.gmail.com:587'
     smtp_from: 'alerts@openshub.com'
     smtp_auth_username: 'alerts@openshub.com'
     smtp_auth_password: 'your-app-password'  # 确保密码正确
   ```

2. **检查网络连接**
   ```bash
   # 测试 SMTP 服务器连通性
   telnet smtp.gmail.com 587
   ```

3. **验证 Webhook 配置**
   ```bash
   # 测试 Webhook URL 可访问性
   curl -X POST http://backend:8080/api/v1/alerts/webhook
   ```

## 5. 可视化问题排查

### 5.1 Grafana 无法显示数据

#### 问题现象
- Grafana 仪表板显示 "No data"
- 查询返回空结果
- 数据源连接失败

#### 诊断步骤
1. **检查数据源配置**
   ```bash
   # 访问 Grafana 数据源配置页面
   # http://localhost:3001/datasources
   ```

2. **测试数据源连接**
   ```bash
   # 在数据源配置页面点击 "Save & Test"
   ```

3. **验证 Prometheus 状态**
   ```bash
   # 检查 Prometheus 是否正常运行
   docker ps | grep prometheus
   ```

#### 解决方案
1. **修复数据源配置**
   ```yaml
   # monitoring/grafana/provisioning/datasources/prometheus.yml
   apiVersion: 1
   datasources:
     - name: Prometheus
       type: prometheus
       url: http://prometheus:9090  # 确保 URL 正确
   ```

2. **重启 Grafana**
   ```bash
   docker restart grafana
   ```

### 5.2 图表渲染异常

#### 问题现象
- 图表显示不完整
- 数据点缺失
- 时间轴显示异常

#### 诊断步骤
1. **检查查询表达式**
   ```promql
   # 在 Grafana 查询编辑器中验证表达式
   ipmi_temperature_celsius
   ```

2. **查看数据范围**
   ```bash
   # 检查查询时间范围设置
   ```

3. **检查面板配置**
   ```bash
   # 检查面板的可视化设置
   ```

#### 解决方案
1. **优化查询表达式**
   ```promql
   # 添加标签过滤减少数据量
   ipmi_temperature_celsius{job="ipmi-servers"}
   ```

2. **调整面板设置**
   - 增加数据点采样间隔
   - 调整时间范围设置
   - 优化可视化选项

### 5.3 仪表板加载缓慢

#### 问题现象
- 仪表板加载时间过长
- 图表渲染卡顿
- 页面响应缓慢

#### 诊断步骤
1. **检查系统资源**
   ```bash
   docker stats grafana prometheus
   ```

2. **分析查询性能**
   ```promql
   # 在 Prometheus Graph 页面测试查询性能
   rate(ipmi_temperature_celsius[5m])
   ```

3. **查看网络延迟**
   ```bash
   ping prometheus
   ```

#### 解决方案
1. **优化查询**
   ```promql
   # 减少查询的数据量
   ipmi_temperature_celsius[1h]  # 缩短时间范围
   ```

2. **增加资源限制**
   ```yaml
   # docker-compose.monitoring.yml
   grafana:
     mem_limit: 2g
     cpus: 1.0
   ```

3. **启用查询缓存**
   ```yaml
   # Prometheus 配置优化
   query:
     lookback_delta: 5m
     timeout: 2m
   ```

## 6. 系统性能问题排查

### 6.1 组件响应缓慢

#### 问题现象
- Prometheus 查询响应慢
- AlertManager 处理延迟
- Grafana 页面加载慢

#### 诊断步骤
1. **检查资源使用**
   ```bash
   docker stats prometheus alertmanager grafana
   ```

2. **分析系统负载**
   ```bash
   top
   iostat -x 1
   ```

3. **查看组件日志**
   ```bash
   docker logs prometheus --tail 100
   ```

#### 解决方案
1. **增加资源分配**
   ```yaml
   # docker-compose.monitoring.yml
   prometheus:
     mem_limit: 4g
     cpus: 2.0
   ```

2. **优化配置**
   ```yaml
   # prometheus.yml
   global:
     scrape_interval: 60s  # 适当增加采集间隔
   ```

### 6.2 资源使用过高

#### 问题现象
- CPU 使用率持续高位
- 内存占用过大
- 磁盘空间不足

#### 诊断步骤
1. **监控资源使用**
   ```bash
   docker stats
   df -h
   ```

2. **分析内存使用**
   ```bash
   docker exec prometheus ps aux
   ```

3. **检查数据保留**
   ```bash
   # 检查 Prometheus 数据目录大小
   du -sh /var/lib/docker/volumes/prometheus_data
   ```

#### 解决方案
1. **调整数据保留**
   ```yaml
   # docker-compose.monitoring.yml
   command:
     - '--storage.tsdb.retention.time=30d'  # 减少数据保留时间
   ```

2. **优化查询**
   - 避免复杂的聚合查询
   - 减少不必要的标签匹配
   - 使用更精确的时间范围

### 6.3 系统不稳定

#### 问题现象
- 组件频繁重启
- 服务不可用
- 数据丢失

#### 诊断步骤
1. **检查容器状态**
   ```bash
   docker ps -a
   ```

2. **查看重启日志**
   ```bash
   docker events --filter container=prometheus
   ```

3. **分析系统日志**
   ```bash
   journalctl -u docker
   ```

#### 解决方案
1. **增加稳定性配置**
   ```yaml
   # docker-compose.monitoring.yml
   restart: unless-stopped
   healthcheck:
     test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
     interval: 30s
     timeout: 10s
     retries: 3
   ```

2. **优化系统配置**
   - 增加系统内存和存储
   - 优化 Docker 存储驱动
   - 调整内核参数

## 7. 配置问题排查

### 7.1 配置文件错误

#### 问题现象
- 组件启动失败
- 配置不生效
- 语法错误提示

#### 诊断步骤
1. **验证配置语法**
   ```bash
   # 检查 YAML 语法
   python -c "import yaml; yaml.safe_load(open('monitoring/prometheus/prometheus.yml'))"
   ```

2. **查看错误日志**
   ```bash
   docker logs prometheus
   ```

3. **测试配置加载**
   ```bash
   # 使用配置测试工具
   promtool check config monitoring/prometheus/prometheus.yml
   ```

#### 解决方案
1. **修复语法错误**
   ```yaml
   # 确保 YAML 缩进正确
   # 确保引号使用正确
   # 确保特殊字符转义正确
   ```

2. **重新加载配置**
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```

### 7.2 权限配置问题

#### 问题现象
- API 访问被拒绝
- 文件访问权限不足
- 认证失败

#### 诊断步骤
1. **检查文件权限**
   ```bash
   ls -la monitoring/prometheus/
   ```

2. **验证用户权限**
   ```bash
   # 检查 Docker 容器用户权限
   docker exec prometheus ls -la /etc/prometheus/
   ```

3. **测试 API 访问**
   ```bash
   curl -H "Authorization: Bearer token" http://localhost:8000/api/v1/monitoring/prometheus/query?query=up
   ```

#### 解决方案
1. **调整文件权限**
   ```bash
   chmod 644 monitoring/prometheus/prometheus.yml
   ```

2. **修复认证配置**
   ```yaml
   # 确保认证配置正确
   global:
     scrape_interval: 30s
   ```

### 7.3 网络配置问题

#### 问题现象
- 组件间通信失败
- 网络连接超时
- DNS 解析失败

#### 诊断步骤
1. **检查网络连接**
   ```bash
   docker network ls
   docker network inspect monitoring
   ```

2. **测试连通性**
   ```bash
   docker exec prometheus ping alertmanager
   ```

3. **验证端口映射**
   ```bash
   docker port prometheus
   ```

#### 解决方案
1. **修复网络配置**
   ```yaml
   # docker-compose.monitoring.yml
   networks:
     monitoring:
       driver: bridge
   ```

2. **检查防火墙设置**
   ```bash
   # 确保所需端口未被防火墙阻止
   sudo ufw status
   ```

## 8. 预防性维护

### 8.1 定期检查清单

#### 每日检查
- [ ] 检查各组件运行状态
- [ ] 查看系统资源使用情况
- [ ] 检查未处理的告警

#### 每周检查
- [ ] 审查告警规则有效性
- [ ] 验证备份策略执行情况
- [ ] 检查配置文件变更

#### 每月检查
- [ ] 性能基准测试
- [ ] 安全配置审查
- [ ] 知识库更新

### 8.2 监控系统健康

#### 健康指标
- 组件可用性 > 99.9%
- 查询响应时间 < 1秒
- 告警处理延迟 < 1分钟

#### 监控策略
- 建立系统自监控
- 设置健康检查告警
- 定期生成健康报告

## 9. 应急响应

### 9.1 故障恢复流程

#### 紧急响应
1. 确认故障影响范围
2. 启动应急预案
3. 实施临时解决方案

#### 恢复步骤
1. 分析故障根本原因
2. 实施永久性修复
3. 验证修复效果
4. 更新文档和流程

### 9.2 备份和恢复

#### 备份策略
- 定期备份配置文件
- 自动备份监控数据
- 异地备份关键数据

#### 恢复流程
1. 确认备份数据完整性
2. 停止相关服务
3. 恢复备份数据
4. 启动服务并验证

## 10. 总结

通过遵循本指南中的故障排除步骤和解决方案，可以快速诊断和解决 OpenServerHub 监控系统中的常见问题。关键是要建立完善的监控和告警机制，定期进行系统维护，并持续优化系统配置和性能。