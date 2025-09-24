# 监控系统告警设计

## 1. 概述

本文档详细描述 OpenServerHub 监控系统的告警设计，包括告警规则、处理流程和通知机制。

## 2. 告警规则设计

### 2.1 CPU 温度告警
```yaml
# monitoring/prometheus/rules/hardware_alerts.yml
- alert: HighCPUTemperature
  expr: ipmi_temperature_celsius{name=~".*CPU.*"} > 80
  for: 2m
  labels:
    severity: warning
    component: cpu
  annotations:
    summary: "CPU温度过高"
    description: "服务器 {{ $labels.server_name }} CPU温度达到 {{ $value }}°C"
```

### 2.2 风扇故障告警
```yaml
- alert: FanFailure
  expr: ipmi_fan_speed_rpm == 0
  for: 30s
  labels:
    severity: critical
    component: fan
  annotations:
    summary: "风扇故障"
    description: "服务器 {{ $labels.server_name }} 风扇停止转动"
```

### 2.3 服务器离线告警
```yaml
- alert: ServerDown
  expr: up{job="ipmi-servers"} == 0
  for: 5m
  labels:
    severity: critical
    component: connectivity
  annotations:
    summary: "服务器离线"
    description: "服务器 {{ $labels.server_name }} 无法连接"
```

### 2.4 电压异常告警
```yaml
- alert: VoltageAnomaly
  expr: abs(ipmi_voltage_volts - 3.3) > 0.3
  for: 1m
  labels:
    severity: warning
    component: voltage
  annotations:
    summary: "电压异常"
    description: "服务器 {{ $labels.server_name }} 电压 {{ $labels.name }} 达到 {{ $value }}V"
```

## 3. 告警处理流程

### 3.1 告警生命周期
1. **触发**: Prometheus 根据规则评估触发告警
2. **发送**: Prometheus 将告警发送给 AlertManager
3. **分组**: AlertManager 对告警进行分组和去重
4. **通知**: AlertManager 发送通知给指定接收者
5. **处理**: 系统接收告警 Webhook 并记录到数据库
6. **解决**: 问题解决后告警自动清除

### 3.2 告警分组策略
```yaml
# monitoring/alertmanager/alertmanager.yml
route:
  group_by: ['alertname', 'cluster', 'server_name']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    # 严重告警立即通知
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 0s
      repeat_interval: 5m
```

## 4. 通知机制设计

### 4.1 邮件通知
```yaml
receivers:
  - name: 'default'
    email_configs:
      - to: 'admin@openshub.com'
        subject: '[OpenServerHub] {{ .Status | toUpper }} - {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          告警名称: {{ .Annotations.summary }}
          告警详情: {{ .Annotations.description }}
          触发时间: {{ .StartsAt.Format "2006-01-02 15:04:05" }}
          服务器: {{ .Labels.server_name }}
          {{ end }}
```

### 4.2 Webhook 通知
```yaml
  - name: 'critical-alerts'
    email_configs:
      - to: 'critical@openshub.com'
        subject: '[CRITICAL] {{ .GroupLabels.alertname }}'
    webhook_configs:
      - url: 'http://backend:8080/api/v1/alerts/webhook'
        send_resolved: true
```

### 4.3 Webhook 处理
```python
# app/api/v1/endpoints/monitoring.py
@router.post("/alerts/webhook")
async def handle_alert_webhook(
    alert_data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """处理AlertManager告警Webhook"""
    try:
        # 记录告警信息到数据库
        # 这里可以添加具体的告警处理逻辑
        
        # 如果需要异步处理，可以添加到后台任务
        # background_tasks.add_task(process_alert, alert_data)
        
        return {"status": "success", "message": "告警已接收"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## 5. 告警级别定义

### 5.1 告警严重程度
| 级别 | 描述 | 响应时间 | 通知方式 |
|------|------|----------|----------|
| Critical | 严重告警，需要立即处理 | 立即 | 邮件、短信、电话 |
| Warning | 警告告警，需要关注 | 15分钟内 | 邮件 |
| Info | 信息性告警，仅供参考 | 1小时内 | 邮件（可选） |

### 5.2 告警分类
| 类别 | 组件 | 描述 |
|------|------|------|
| Hardware | CPU | CPU 温度、使用率等 |
| Hardware | Fan | 风扇转速、故障等 |
| Hardware | Voltage | 电压异常等 |
| Connectivity | Network | 网络连接状态 |
| System | OS | 系统资源使用情况 |

## 6. 告警抑制和静默

### 6.1 告警抑制
```yaml
# 避免在服务器离线时产生其他告警
inhibit_rules:
  - source_match:
      alertname: ServerDown
    target_match:
      component: cpu
    equal: ['server_name']
```

### 6.2 告警静默
可以通过 AlertManager API 或界面创建静默规则，临时屏蔽特定告警。

## 7. 告警历史记录

### 7.1 数据库设计
```sql
CREATE TABLE alert_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_name VARCHAR(100) NOT NULL,
    server_id INTEGER,
    server_name VARCHAR(100),
    severity VARCHAR(20),
    status VARCHAR(20), -- firing, resolved
    summary TEXT,
    description TEXT,
    starts_at TIMESTAMP,
    ends_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.2 告警记录服务
```python
class AlertRecordService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_alert_record(self, alert_data: dict) -> AlertRecord:
        """创建告警记录"""
        record = AlertRecord(
            alert_name=alert_data.get('alertname'),
            server_id=alert_data.get('server_id'),
            server_name=alert_data.get('server_name'),
            severity=alert_data.get('severity'),
            status=alert_data.get('status', 'firing'),
            summary=alert_data.get('summary'),
            description=alert_data.get('description'),
            starts_at=alert_data.get('starts_at'),
            ends_at=alert_data.get('ends_at')
        )
        self.db.add(record)
        self.db.commit()
        return record
```

## 8. 告警测试

### 8.1 告警规则测试
```bash
# 测试告警规则
curl -X POST "http://localhost:9090/api/v1/query?query=ipmi_temperature_celsius%20%3E%2080"
```

### 8.2 告警通知测试
```bash
# 发送测试告警到 AlertManager
curl -X POST "http://localhost:9093/api/v1/alerts" \
  -H "Content-Type: application/json" \
  -d '[{
    "status": "firing",
    "labels": {
      "alertname": "TestAlert",
      "service": "test-service",
      "severity":"critical"
    },
    "annotations": {
      "summary": "测试告警",
      "description": "这是一个测试告警"
    },
    "generatorURL": "http://prometheus:9090/graph?g0.expr=up&g0.tab=1"
  }]'
```

## 9. 告警优化建议

### 9.1 告警规则优化
1. 避免过于敏感的阈值设置
2. 合理设置告警持续时间
3. 使用合适的标签进行分组

### 9.2 通知优化
1. 避免告警风暴
2. 提供清晰的告警信息
3. 支持告警升级机制

### 9.3 性能优化
1. 限制同时处理的告警数量
2. 优化告警处理逻辑
3. 使用异步处理提高性能

## 10. 告警监控

### 10.1 告警系统健康监控
- 监控 AlertManager 自身状态
- 监控告警处理延迟
- 监控通知发送成功率

### 10.2 告警统计
- 告警触发频率统计
- 告警解决时间统计
- 告警分类统计