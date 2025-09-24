# 监控系统API设计

## 1. 概述

本文档详细说明 OpenServerHub 监控系统的 API 接口设计，包括监控数据查询、Prometheus 集成、告警处理等接口。

## 2. API 端点概览

### 2.1 监控数据接口
- `GET /api/v1/monitoring/servers/{server_id}/metrics` - 获取服务器监控指标
- `POST /api/v1/monitoring/servers/{server_id}/collect` - 手动采集服务器指标

### 2.2 Prometheus 集成接口
- `GET /api/v1/monitoring/prometheus/query` - 查询 Prometheus 监控数据
- `GET /api/v1/monitoring/prometheus/query_range` - 查询 Prometheus 监控数据范围

### 2.3 告警处理接口
- `POST /api/v1/monitoring/alerts/webhook` - AlertManager 告警 Webhook

## 3. 监控数据接口

### 3.1 获取服务器监控指标

#### 接口详情
- **URL**: `GET /api/v1/monitoring/servers/{server_id}/metrics`
- **方法**: `GET`
- **认证**: 需要 JWT Token
- **权限**: 需要相应权限

#### 请求参数
| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| server_id | integer | 是 | 服务器ID |
| metric_type | string | 否 | 指标类型 (temperature, voltage, fan_speed) |
| hours | integer | 否 | 获取最近N小时的数据，默认24小时 |

#### 响应格式
```json
[
  {
    "id": 1,
    "server_id": 1,
    "metric_type": "temperature",
    "metric_name": "CPU1 Temp",
    "value": 45.2,
    "unit": "celsius",
    "status": "ok",
    "threshold_min": 0,
    "threshold_max": 80,
    "timestamp": "2023-12-01T10:30:00Z"
  }
]
```

#### 示例请求
```bash
curl -X GET "http://localhost:8000/api/v1/monitoring/servers/1/metrics?metric_type=temperature&hours=24" \
  -H "Authorization: Bearer <token>"
```

#### 示例响应
```json
[
  {
    "id": 1,
    "server_id": 1,
    "metric_type": "temperature",
    "metric_name": "CPU1 Temp",
    "value": 45.2,
    "unit": "celsius",
    "status": "ok",
    "threshold_min": 0,
    "threshold_max": 80,
    "timestamp": "2023-12-01T10:30:00Z"
  },
  {
    "id": 2,
    "server_id": 1,
    "metric_type": "temperature",
    "metric_name": "CPU2 Temp",
    "value": 43.8,
    "unit": "celsius",
    "status": "ok",
    "threshold_min": 0,
    "threshold_max": 80,
    "timestamp": "2023-12-01T10:30:00Z"
  }
]
```

### 3.2 手动采集服务器指标

#### 接口详情
- **URL**: `POST /api/v1/monitoring/servers/{server_id}/collect`
- **方法**: `POST`
- **认证**: 需要 JWT Token
- **权限**: 需要相应权限

#### 请求参数
| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| server_id | integer | 是 | 服务器ID |

#### 响应格式
```json
{
  "status": "success",
  "collected_metrics": [
    "temperature:CPU1 Temp",
    "temperature:CPU2 Temp",
    "fan_speed:Fan1"
  ],
  "timestamp": "2023-12-01T10:30:00Z"
}
```

#### 示例请求
```bash
curl -X POST "http://localhost:8000/api/v1/monitoring/servers/1/collect" \
  -H "Authorization: Bearer <token>"
```

#### 示例响应
```json
{
  "status": "success",
  "collected_metrics": [
    "temperature:CPU1 Temp",
    "temperature:CPU2 Temp",
    "fan_speed:Fan1",
    "voltage:3.3V"
  ],
  "timestamp": "2023-12-01T10:30:00Z"
}
```

## 4. Prometheus 集成接口

### 4.1 查询 Prometheus 监控数据

#### 接口详情
- **URL**: `GET /api/v1/monitoring/prometheus/query`
- **方法**: `GET`
- **认证**: 需要 JWT Token
- **权限**: 需要相应权限

#### 请求参数
| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| query | string | 是 | Prometheus 查询表达式 |
| time | string | 否 | 查询时间点 |

#### 响应格式
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "__name__": "ipmi_temperature_celsius",
          "instance": "192.168.1.100:9290",
          "job": "ipmi-servers",
          "name": "CPU1 Temp",
          "server_id": "1",
          "server_name": "server-01"
        },
        "value": [
          1606868400,
          "45.2"
        ]
      }
    ]
  }
}
```

#### 示例请求
```bash
curl -X GET "http://localhost:8000/api/v1/monitoring/prometheus/query?query=ipmi_temperature_celsius" \
  -H "Authorization: Bearer <token>"
```

#### 示例响应
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "__name__": "ipmi_temperature_celsius",
          "instance": "192.168.1.100:9290",
          "job": "ipmi-servers",
          "name": "CPU1 Temp",
          "server_id": "1",
          "server_name": "server-01"
        },
        "value": [
          1606868400,
          "45.2"
        ]
      }
    ]
  }
}
```

### 4.2 查询 Prometheus 监控数据范围

#### 接口详情
- **URL**: `GET /api/v1/monitoring/prometheus/query_range`
- **方法**: `GET`
- **认证**: 需要 JWT Token
- **权限**: 需要相应权限

#### 请求参数
| 参数名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| query | string | 是 | Prometheus 查询表达式 |
| start | string | 是 | 开始时间 |
| end | string | 是 | 结束时间 |
| step | string | 否 | 时间步长，默认60s |

#### 响应格式
```json
{
  "status": "success",
  "data": {
    "resultType": "matrix",
    "result": [
      {
        "metric": {
          "__name__": "ipmi_temperature_celsius",
          "instance": "192.168.1.100:9290",
          "job": "ipmi-servers",
          "name": "CPU1 Temp",
          "server_id": "1",
          "server_name": "server-01"
        },
        "values": [
          [
            1606868400,
            "45.2"
          ],
          [
            1606868460,
            "45.3"
          ]
        ]
      }
    ]
  }
}
```

#### 示例请求
```bash
curl -X GET "http://localhost:8000/api/v1/monitoring/prometheus/query_range?query=ipmi_temperature_celsius&start=2023-12-01T10:00:00Z&end=2023-12-01T11:00:00Z&step=60s" \
  -H "Authorization: Bearer <token>"
```

#### 示例响应
```json
{
  "status": "success",
  "data": {
    "resultType": "matrix",
    "result": [
      {
        "metric": {
          "__name__": "ipmi_temperature_celsius",
          "instance": "192.168.1.100:9290",
          "job": "ipmi-servers",
          "name": "CPU1 Temp",
          "server_id": "1",
          "server_name": "server-01"
        },
        "values": [
          [
            1606868400,
            "45.2"
          ],
          [
            1606868460,
            "45.3"
          ],
          [
            1606868520,
            "45.1"
          ]
        ]
      }
    ]
  }
}
```

## 5. 告警处理接口

### 5.1 AlertManager 告警 Webhook

#### 接口详情
- **URL**: `POST /api/v1/monitoring/alerts/webhook`
- **方法**: `POST`
- **认证**: 无需认证（由 AlertManager 调用）
- **权限**: 无需权限

#### 请求体格式
```json
{
  "version": "4",
  "groupKey": "{}:{alertname=\"HighCPUTemperature\"}",
  "status": "firing",
  "receiver": "default",
  "groupLabels": {
    "alertname": "HighCPUTemperature"
  },
  "commonLabels": {
    "alertname": "HighCPUTemperature",
    "component": "cpu",
    "severity": "warning"
  },
  "commonAnnotations": {
    "summary": "CPU温度过高",
    "description": "服务器 server-01 CPU温度达到 82.5°C"
  },
  "externalURL": "http://alertmanager:9093",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighCPUTemperature",
        "component": "cpu",
        "severity": "warning",
        "server_id": "1",
        "server_name": "server-01"
      },
      "annotations": {
        "summary": "CPU温度过高",
        "description": "服务器 server-01 CPU温度达到 82.5°C"
      },
      "startsAt": "2023-12-01T10:30:00Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus:9090/graph?g0.expr=ipmi_temperature_celsius...",
      "fingerprint": "abcdef1234567890"
    }
  ]
}
```

#### 响应格式
```json
{
  "status": "success",
  "message": "告警已接收"
}
```

#### 示例请求
```bash
curl -X POST "http://localhost:8000/api/v1/monitoring/alerts/webhook" \
  -H "Content-Type: application/json" \
  -d '{
  "version": "4",
  "groupKey": "{}:{alertname=\"HighCPUTemperature\"}",
  "status": "firing",
  "receiver": "default",
  "groupLabels": {
    "alertname": "HighCPUTemperature"
  },
  "commonLabels": {
    "alertname": "HighCPUTemperature",
    "component": "cpu",
    "severity": "warning"
  },
  "commonAnnotations": {
    "summary": "CPU温度过高",
    "description": "服务器 server-01 CPU温度达到 82.5°C"
  },
  "externalURL": "http://alertmanager:9093",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighCPUTemperature",
        "component": "cpu",
        "severity": "warning",
        "server_id": "1",
        "server_name": "server-01"
      },
      "annotations": {
        "summary": "CPU温度过高",
        "description": "服务器 server-01 CPU温度达到 82.5°C"
      },
      "startsAt": "2023-12-01T10:30:00Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus:9090/graph?g0.expr=ipmi_temperature_celsius...",
      "fingerprint": "abcdef1234567890"
    }
  ]
}'
```

#### 示例响应
```json
{
  "status": "success",
  "message": "告警已接收"
}
```

## 6. 错误响应格式

### 6.1 通用错误格式
```json
{
  "detail": "错误描述信息"
}
```

### 6.2 认证错误
```json
{
  "detail": "Not authenticated"
}
```

### 6.3 权限错误
```json
{
  "detail": "Not enough permissions"
}
```

### 6.4 参数验证错误
```json
{
  "detail": [
    {
      "loc": [
        "query",
        "server_id"
      ],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## 7. API 使用示例

### 7.1 Python 客户端示例
```python
import requests
import json

class MonitoringAPIClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def get_server_metrics(self, server_id, metric_type=None, hours=24):
        """获取服务器监控指标"""
        url = f"{self.base_url}/api/v1/monitoring/servers/{server_id}/metrics"
        params = {"hours": hours}
        if metric_type:
            params["metric_type"] = metric_type
            
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def collect_server_metrics(self, server_id):
        """手动采集服务器指标"""
        url = f"{self.base_url}/api/v1/monitoring/servers/{server_id}/collect"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def query_prometheus(self, query, time=None):
        """查询Prometheus监控数据"""
        url = f"{self.base_url}/api/v1/monitoring/prometheus/query"
        params = {"query": query}
        if time:
            params["time"] = time
            
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

# 使用示例
client = MonitoringAPIClient("http://localhost:8000", "your-jwt-token")

# 获取服务器温度指标
metrics = client.get_server_metrics(1, "temperature", 24)
print(json.dumps(metrics, indent=2))

# 手动采集服务器指标
result = client.collect_server_metrics(1)
print(json.dumps(result, indent=2))

# 查询Prometheus数据
prom_data = client.query_prometheus("ipmi_temperature_celsius")
print(json.dumps(prom_data, indent=2))
```

### 7.2 JavaScript 客户端示例
```javascript
class MonitoringAPIClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }
  
  async getServerMetrics(serverId, metricType = null, hours = 24) {
    const params = new URLSearchParams({
      hours: hours
    });
    
    if (metricType) {
      params.append('metric_type', metricType);
    }
    
    const response = await fetch(
      `${this.baseUrl}/api/v1/monitoring/servers/${serverId}/metrics?${params}`,
      {
        method: 'GET',
        headers: this.headers
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }
  
  async collectServerMetrics(serverId) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/monitoring/servers/${serverId}/collect`,
      {
        method: 'POST',
        headers: this.headers
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }
  
  async queryPrometheus(query, time = null) {
    const params = new URLSearchParams({
      query: query
    });
    
    if (time) {
      params.append('time', time);
    }
    
    const response = await fetch(
      `${this.baseUrl}/api/v1/monitoring/prometheus/query?${params}`,
      {
        method: 'GET',
        headers: this.headers
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  }
}

// 使用示例
const client = new MonitoringAPIClient('http://localhost:8000', 'your-jwt-token');

// 获取服务器温度指标
client.getServerMetrics(1, 'temperature', 24)
  .then(metrics => console.log(JSON.stringify(metrics, null, 2)))
  .catch(error => console.error('Error:', error));

// 手动采集服务器指标
client.collectServerMetrics(1)
  .then(result => console.log(JSON.stringify(result, null, 2)))
  .catch(error => console.error('Error:', error));

// 查询Prometheus数据
client.queryPrometheus('ipmi_temperature_celsius')
  .then(promData => console.log(JSON.stringify(promData, null, 2)))
  .catch(error => console.error('Error:', error));
```

## 8. API 测试

### 8.1 使用 Postman 测试

1. 创建新的请求集合
2. 添加认证头: `Authorization: Bearer <your-token>`
3. 测试各个端点

### 8.2 使用 curl 测试

```bash
# 获取服务器监控指标
curl -X GET "http://localhost:8000/api/v1/monitoring/servers/1/metrics?metric_type=temperature&hours=24" \
  -H "Authorization: Bearer <your-token>"

# 手动采集服务器指标
curl -X POST "http://localhost:8000/api/v1/monitoring/servers/1/collect" \
  -H "Authorization: Bearer <your-token>"

# 查询Prometheus数据
curl -X GET "http://localhost:8000/api/v1/monitoring/prometheus/query?query=ipmi_temperature_celsius" \
  -H "Authorization: Bearer <your-token>"
```

## 9. API 安全

### 9.1 认证机制
- 使用 JWT Token 进行认证
- Token 通过 `/api/v1/auth/login` 接口获取

### 9.2 权限控制
- 不同用户角色具有不同的 API 访问权限
- 管理员可以访问所有监控接口
- 普通用户只能查看自己有权限的服务器监控数据

### 9.3 数据保护
- 敏感数据通过 HTTPS 传输
- 日志记录所有 API 访问
- 定期审计 API 使用情况

## 10. API 性能优化

### 10.1 分页查询
对于大量数据的查询，应实现分页机制：

```python
# 示例：分页查询监控数据
@app.get("/api/v1/monitoring/servers/{server_id}/metrics")
async def get_server_metrics(
    server_id: int,
    metric_type: str = Query(None),
    hours: int = Query(24),
    skip: int = Query(0),
    limit: int = Query(100)
):
    # 实现分页查询逻辑
    pass
```

### 10.2 缓存机制
对于频繁查询的数据，应实现缓存机制：

```python
# 示例：使用 Redis 缓存监控数据
from redis import Redis

redis_client = Redis(host='localhost', port=6379, db=0)

@app.get("/api/v1/monitoring/servers/{server_id}/metrics")
async def get_server_metrics(server_id: int):
    # 尝试从缓存获取数据
    cache_key = f"server_metrics:{server_id}"
    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        return json.loads(cached_data)
    
    # 从数据库获取数据
    data = get_metrics_from_db(server_id)
    
    # 将数据存入缓存
    redis_client.setex(cache_key, 300, json.dumps(data))  # 缓存5分钟
    
    return data
```

### 10.3 异步处理
对于耗时操作，应使用异步处理：

```python
# 示例：异步采集监控数据
@app.post("/api/v1/monitoring/servers/{server_id}/collect")
async def collect_server_metrics(
    server_id: int,
    background_tasks: BackgroundTasks
):
    # 将采集任务添加到后台执行
    background_tasks.add_task(collect_metrics_async, server_id)
    
    return {"status": "started", "message": "数据采集任务已启动"}
```