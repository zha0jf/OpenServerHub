# API接口设计

## API设计原则

### RESTful设计
- 使用HTTP动词表示操作：GET(查询)、POST(创建)、PUT(更新)、DELETE(删除)
- 使用名词表示资源：/servers、/clusters、/users
- 使用HTTP状态码表示结果：200(成功)、201(创建)、400(错误)、401(未授权)、404(未找到)
- 统一的响应格式和错误处理

### 版本控制
- API版本通过URL路径控制：`/api/v1/servers`
- 向后兼容原则，新版本不破坏现有功能
- 废弃版本提前通知和迁移期

### 安全设计
- JWT令牌认证
- 基于角色的权限控制(RBAC)
- 请求速率限制
- 操作审计日志

## 通用响应格式

### 成功响应
```json
{
  "success": true,
  "data": {
    // 具体数据
  },
  "message": "操作成功",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": [
      {
        "field": "bmc_ip",
        "message": "IP地址格式无效"
      }
    ]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 分页响应
```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 150,
      "total_pages": 8
    }
  }
}
```

## 认证和授权接口

### 用户认证
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password123"
}

# 响应
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
}
```

```http
POST /api/v1/auth/refresh
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400
  }
}
```

```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "message": "登出成功"
}
```

### 用户信息
```http
GET /api/v1/auth/profile
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "last_login_at": "2024-01-15T09:30:00Z",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

## 服务器管理接口

### 服务器列表
```http
GET /api/v1/servers?page=1&size=20&cluster_id=1&search=web
Authorization: Bearer <access_token>

# 查询参数
# page: 页码，默认1
# size: 每页数量，默认20，最大100
# cluster_id: 集群ID筛选
# search: 搜索关键词（服务器名称、IP地址）
# power_state: 电源状态筛选(on/off/unknown)
# health_status: 健康状态筛选(ok/warning/critical)

# 响应
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "web-server-01",
        "ipmi_ip": "192.168.1.100",
        "ipmi_port": 623,
        "manufacturer": "Dell",
        "model": "PowerEdge R740",
        "serial_number": "ABC123456",
        "power_state": "on",
        "health_status": "ok",
        "last_seen": "2024-01-15T10:25:00Z",
        "cluster": {
          "id": 1,
          "name": "Web服务器集群"
        },
        "monitoring_enabled": true,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 150,
      "total_pages": 8
    }
  }
}
```

### 服务器详情
```http
GET /api/v1/servers/1
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "id": 1,
    "name": "web-server-01",
    "ipmi_ip": "192.168.1.100",
    "ipmi_port": 623,
    "ipmi_username": "admin",
    "manufacturer": "Dell",
    "model": "PowerEdge R740",
    "serial_number": "ABC123456",
    "asset_tag": "IT-001",
    "rack_location": "机柜A-01",
    "rack_unit": "1U",
    "datacenter": "北京机房",
    "power_state": "on",
    "health_status": "ok",
    "connection_status": "connected",
    "monitoring_enabled": true,
    "monitoring_interval": 60,
    "last_seen": "2024-01-15T10:25:00Z",
    "last_check": "2024-01-15T10:25:00Z",
    "cluster": {
      "id": 1,
      "name": "Web服务器集群",
      "description": "前端Web服务器集群"
    },
    "metadata": {
      "environment": "production",
      "owner": "DevOps团队"
    },
    "tags": ["web", "production", "critical"],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
}
```

### 创建服务器
```http
POST /api/v1/servers
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "web-server-02",
  "ipmi_ip": "192.168.1.101",
  "ipmi_port": 623,
  "ipmi_username": "admin",
  "ipmi_password": "password123",
  "manufacturer": "Dell",
  "model": "PowerEdge R740",
  "serial_number": "ABC123457",
  "asset_tag": "IT-002",
  "rack_location": "机柜A-02",
  "datacenter": "北京机房",
  "cluster_id": 1,
  "monitoring_enabled": true,
  "metadata": {
    "environment": "production",
    "owner": "DevOps团队"
  },
  "tags": ["web", "production"]
}

# 响应
{
  "success": true,
  "data": {
    "id": 2,
    "name": "web-server-02",
    // ... 完整服务器信息
  },
  "message": "服务器创建成功"
}
```

### 更新服务器
```http
PUT /api/v1/servers/1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "web-server-01-updated",
  "monitoring_enabled": false,
  "tags": ["web", "production", "updated"]
}

# 响应
{
  "success": true,
  "data": {
    "id": 1,
    "name": "web-server-01-updated",
    // ... 更新后的服务器信息
  },
  "message": "服务器更新成功"
}
```

### 删除服务器
```http
DELETE /api/v1/servers/1
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "message": "服务器删除成功"
}
```

## 服务器操作接口

### 电源控制
```http
POST /api/v1/servers/1/power/on
Authorization: Bearer <access_token>

# 支持的操作: on, off, reset, cycle
# on: 开机
# off: 关机
# reset: 重启
# cycle: 强制重启

# 响应
{
  "success": true,
  "data": {
    "operation": "power_on",
    "result": "命令执行成功",
    "previous_state": "off",
    "current_state": "on",
    "executed_at": "2024-01-15T10:30:00Z"
  },
  "message": "电源操作执行成功"
}
```

### 获取服务器状态
```http
GET /api/v1/servers/1/status
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "power_state": "on",
    "health_status": "ok",
    "connection_status": "connected",
    "last_check": "2024-01-15T10:30:00Z",
    "uptime": 86400,
    "system_info": {
      "bios_version": "2.10.0",
      "firmware_version": "4.40.40.40"
    }
  }
}
```

### 获取传感器数据
```http
GET /api/v1/servers/1/sensors
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "timestamp": "2024-01-15T10:30:00Z",
    "sensors": {
      "temperature": [
        {
          "name": "CPU1 Temp",
          "value": 45.0,
          "unit": "celsius",
          "status": "ok",
          "threshold": {
            "warning": 70,
            "critical": 85
          }
        },
        {
          "name": "CPU2 Temp", 
          "value": 47.0,
          "unit": "celsius",
          "status": "ok"
        }
      ],
      "fan_speed": [
        {
          "name": "Fan1",
          "value": 3200,
          "unit": "rpm",
          "status": "ok"
        }
      ],
      "voltage": [
        {
          "name": "12V",
          "value": 12.1,
          "unit": "volts",
          "status": "ok"
        }
      ]
    }
  }
}
```

### 批量操作
```http
POST /api/v1/servers/batch/power/on
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "server_ids": [1, 2, 3, 4, 5],
  "confirm": true
}

# 响应
{
  "success": true,
  "data": {
    "operation": "batch_power_on",
    "total": 5,
    "successful": 4,
    "failed": 1,
    "results": [
      {
        "server_id": 1,
        "success": true,
        "message": "操作成功"
      },
      {
        "server_id": 2,
        "success": true,
        "message": "操作成功"
      },
      {
        "server_id": 3,
        "success": false,
        "error": "连接超时"
      }
    ]
  }
}
```

## 集群管理接口

### 集群列表
```http
GET /api/v1/clusters?page=1&size=20
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "Web服务器集群",
        "description": "前端Web服务器集群",
        "location": "北京机房",
        "server_count": 10,
        "online_servers": 9,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 5,
      "total_pages": 1
    }
  }
}
```

### 集群详情
```http
GET /api/v1/clusters/1
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Web服务器集群",
    "description": "前端Web服务器集群",
    "location": "北京机房",
    "contact_person": "张三",
    "contact_email": "zhangsan@example.com",
    "server_count": 10,
    "online_servers": 9,
    "servers": [
      {
        "id": 1,
        "name": "web-server-01",
        "bmc_ip": "192.168.1.100",
        "power_state": "on",
        "health_status": "ok"
      }
    ],
    "metadata": {
      "environment": "production",
      "criticality": "high"
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
}
```

### 创建集群
```http
POST /api/v1/clusters
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "数据库服务器集群",
  "description": "MySQL数据库服务器集群",
  "location": "上海机房",
  "contact_person": "李四",
  "contact_email": "lisi@example.com",
  "metadata": {
    "environment": "production",
    "criticality": "critical"
  }
}

# 响应
{
  "success": true,
  "data": {
    "id": 2,
    "name": "数据库服务器集群",
    // ... 完整集群信息
  },
  "message": "集群创建成功"
}
```

### 集群服务器管理
```http
POST /api/v1/clusters/1/servers
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "server_ids": [1, 2, 3]
}

# 响应
{
  "success": true,
  "data": {
    "cluster_id": 1,
    "added_servers": 3,
    "total_servers": 13
  },
  "message": "服务器添加到集群成功"
}
```

```http
DELETE /api/v1/clusters/1/servers/2
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "message": "服务器从集群移除成功"
}
```

## 监控接口

### 监控数据查询
```http
GET /api/v1/monitoring/servers/1/metrics?hours=24&metrics=temperature,fan_speed
Authorization: Bearer <access_token>

# 查询参数
# hours: 时间范围(小时)，默认24
# metrics: 指标类型，逗号分隔

# 响应
{
  "success": true,
  "data": {
    "server_id": 1,
    "time_range": {
      "start": "2024-01-14T10:30:00Z",
      "end": "2024-01-15T10:30:00Z"
    },
    "metrics": {
      "temperature": [
        {
          "name": "CPU1 Temp",
          "data_points": [
            {
              "timestamp": "2024-01-15T10:00:00Z",
              "value": 45.0
            },
            {
              "timestamp": "2024-01-15T10:05:00Z", 
              "value": 46.0
            }
          ]
        }
      ],
      "fan_speed": [
        {
          "name": "Fan1",
          "data_points": [
            {
              "timestamp": "2024-01-15T10:00:00Z",
              "value": 3200
            }
          ]
        }
      ]
    }
  }
}
```

### 告警管理
```http
GET /api/v1/monitoring/alerts?status=firing&severity=critical
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "server_id": 1,
        "alert_rule": "HighCPUTemperature",
        "severity": "warning",
        "title": "CPU温度过高",
        "description": "服务器web-server-01 CPU温度达到82°C",
        "current_value": 82.0,
        "threshold_value": 80.0,
        "status": "firing",
        "fired_at": "2024-01-15T10:25:00Z"
      }
    ]
  }
}
```

```http
POST /api/v1/monitoring/alerts/1/acknowledge
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "comment": "已确认，正在处理"
}

# 响应
{
  "success": true,
  "data": {
    "alert_id": 1,
    "status": "acknowledged",
    "acknowledged_by": "admin",
    "acknowledged_at": "2024-01-15T10:30:00Z"
  },
  "message": "告警确认成功"
}
```

### Grafana集成
```http
POST /api/v1/monitoring/dashboards/servers/1
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "dashboard_uid": "server-1-dashboard",
    "dashboard_url": "http://grafana:3000/d/server-1-dashboard",
    "dashboard_title": "服务器监控 - web-server-01",
    "panels": [
      {
        "id": 1,
        "title": "CPU温度",
        "embed_url": "http://grafana:3000/d-solo/server-1-dashboard?panelId=1&orgId=1"
      }
    ]
  },
  "message": "监控仪表板创建成功"
}
```

## 设备发现接口

### 网络扫描
```http
POST /api/v1/discovery/scan
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "network": "192.168.1.0/24",
  "port": 623,
  "timeout": 10
}

# 响应
{
  "success": true,
  "data": {
    "scan_id": "scan-001",
    "network": "192.168.1.0/24",
    "total_ips": 254,
    "discovered_devices": [
      {
        "ip": "192.168.1.100",
        "port": 623,
        "manufacturer": "Dell",
        "model": "iDRAC",
        "response_time": 150
      }
    ],
    "scan_duration": 30.5
  }
}
```

### 批量导入
```http
POST /api/v1/servers/import
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

# Form data:
# file: CSV文件
# cluster_id: 目标集群ID(可选)

# CSV格式:
# name,bmc_ip,bmc_username,bmc_password,manufacturer,model
# web-server-01,192.168.1.100,admin,password,Dell,R740

# 响应
{
  "success": true,
  "data": {
    "total_rows": 10,
    "successful_imports": 8,
    "failed_imports": 2,
    "errors": [
      {
        "row": 3,
        "error": "IP地址已存在"
      },
      {
        "row": 7,
        "error": "BMC连接失败"
      }
    ]
  },
  "message": "批量导入完成"
}
```

## 系统管理接口

### 系统信息
```http
GET /api/v1/system/info
Authorization: Bearer <access_token>

# 响应
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "build": "20240115-1030",
    "uptime": 86400,
    "database": {
      "type": "postgresql",
      "version": "15.2",
      "status": "connected"
    },
    "monitoring": {
      "prometheus": {
        "status": "connected",
        "targets": 150
      },
      "grafana": {
        "status": "connected",
        "dashboards": 25
      }
    },
    "statistics": {
      "total_servers": 150,
      "online_servers": 145,
      "total_clusters": 8,
      "active_alerts": 3
    }
  }
}
```

### 健康检查
```http
GET /api/v1/health

# 响应（无需认证）
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": "ok",
    "prometheus": "ok", 
    "grafana": "ok"
  }
}
```

## 错误代码说明

| 错误代码 | HTTP状态码 | 说明 |
|---------|-----------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| AUTHENTICATION_REQUIRED | 401 | 需要认证 |
| INVALID_CREDENTIALS | 401 | 认证信息无效 |
| ACCESS_DENIED | 403 | 权限不足 |
| RESOURCE_NOT_FOUND | 404 | 资源不存在 |
| CONFLICT | 409 | 资源冲突 |
| RATE_LIMIT_EXCEEDED | 429 | 请求频率超限 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| IPMI_CONNECTION_ERROR | 502 | IPMI连接失败 |
| EXTERNAL_SERVICE_ERROR | 503 | 外部服务不可用 |

## API限制和配额

### 速率限制
- 认证接口: 10次/分钟
- 查询接口: 100次/分钟  
- 操作接口: 30次/分钟
- 批量操作: 5次/分钟

### 数据限制
- 单次查询最大返回1000条记录
- 批量操作最大支持100个资源
- 文件上传最大10MB
- 请求超时30秒

### 请求示例

```bash
# 使用curl测试API
curl -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'

# 使用令牌访问资源
curl -X GET "http://localhost:8080/api/v1/servers" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```