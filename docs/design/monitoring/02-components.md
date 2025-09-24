# 监控系统核心组件设计

## 1. IPMI Exporter 设计

### 1.1 部署架构
IPMI Exporter 采用独立容器化部署，每个服务器对应一个独立的 Exporter 容器，确保：
1. 隔离性：单个 Exporter 故障不会影响其他服务器监控
2. 可扩展性：支持动态添加/删除 Exporter 实例
3. 简化管理：通过 Docker Compose 统一编排

### 1.2 配置管理
```yaml
# monitoring/ipmi-exporter/ipmi_local.yml
modules:
  default:
    collectors:
    - ipmi
    - dcmi
    exclude_sensor_ids:
    - 2    # 排除特定传感器
    ipmi:
      driver: "LAN_2_0"
      privilege: "user"
      timeout: 10000
      
  dell_servers:
    collectors:
    - ipmi
    - dcmi
    - sel  # 系统事件日志
    ipmi:
      driver: "LAN_2_0" 
      privilege: "user"
      timeout: 15000
```

### 1.3 优势分析
1. **隔离性**：每个 Exporter 独立运行，故障不会相互影响
2. **可扩展性**：支持动态添加/删除服务器时自动管理 Exporter
3. **维护性**：可以独立升级或重启单个 Exporter
4. **安全性**：IPMI 认证信息隔离存储在各自容器中

### 1.4 缺点及解决方案
1. **资源开销**：每个 Exporter 需要独立的容器资源
   - 解决方案：使用轻量级 Alpine 基础镜像，限制内存和 CPU 使用
2. **管理复杂性**：需要管理大量 Exporter 容器
   - 解决方案：通过 Docker Compose 模板化管理，自动化部署

## 2. Prometheus 设计

### 2.1 主配置文件
```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 30s
  evaluation_interval: 30s
  external_labels:
    cluster: 'openshub-cluster'
    environment: 'production'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

rule_files:
  - "rules/*.yml"

scrape_configs:
  # OpenServerHub API监控
  - job_name: 'openshub-api'
    static_configs:
      - targets: ['backend:8080']
    metrics_path: /metrics
    scrape_interval: 15s

  # IPMI服务器监控
  - job_name: 'ipmi-servers'
    file_sd_configs:
      - files:
        - '/etc/prometheus/targets/ipmi-targets.json'
    scrape_interval: 60s
    scrape_timeout: 30s
    metrics_path: /metrics
```

### 2.2 动态目标配置管理
```python
# app/services/prometheus_config.py
class PrometheusConfigManager:
    def __init__(self, config_path: str = "/etc/prometheus/targets/ipmi-targets.json"):
        self.config_path = config_path
        self.reload_url = "http://prometheus:9090/-/reload"
    
    async def sync_ipmi_targets(self, servers: List[Server]) -> bool:
        """根据服务器列表同步IPMI监控目标"""
        try:
            # 生成目标配置
            targets = []
            for server in servers:
                if server.monitoring_enabled:
                    target = {
                        "targets": [f"{server.ipmi_ip}:9290"],
                        "labels": {
                            "server_id": str(server.id),
                            "server_name": server.name,
                            "ipmi_ip": server.ipmi_ip,
                            "manufacturer": server.manufacturer or "unknown"
                        }
                    }
                    targets.append(target)
            
            # 写入配置文件
            config_data = targets
            async with aiofiles.open(self.config_path, 'w') as f:
                await f.write(json.dumps(config_data, indent=2))
            
            # 通知Prometheus重新加载配置
            await self.reload_prometheus()
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync Prometheus config: {e}")
            return False
    
    async def reload_prometheus(self) -> bool:
        """通知Prometheus重新加载配置"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.reload_url)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to reload Prometheus: {e}")
            return False
```

## 3. AlertManager 设计

### 3.1 配置文件
```yaml
# monitoring/alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@openshub.com'
  smtp_auth_username: 'alerts@openshub.com'
  smtp_auth_password: 'your-app-password'

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

  - name: 'critical-alerts'
    email_configs:
      - to: 'critical@openshub.com'
        subject: '[CRITICAL] {{ .GroupLabels.alertname }}'
    webhook_configs:
      - url: 'http://backend:8080/api/v1/alerts/webhook'
        send_resolved: true
```

## 4. Grafana 设计

### 4.1 仪表板自动创建
```python
# app/services/grafana_service.py
class GrafanaService:
    def __init__(self, grafana_url: str, api_key: str):
        self.grafana_url = grafana_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def create_server_dashboard(self, server: Server) -> dict:
        """为服务器创建专用监控仪表板"""
        dashboard_json = {
            "dashboard": {
                "title": f"服务器监控 - {server.name}",
                "tags": ["server", "hardware", "ipmi", f"server-{server.id}"],
                "panels": [
                    self._create_cpu_temperature_panel(server.id),
                    self._create_fan_speed_panel(server.id),
                    self._create_voltage_panel(server.id),
                    self._create_power_status_panel(server.id)
                ]
            },
            "overwrite": True
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.grafana_url}/api/dashboards/db",
                headers=self.headers,
                json=dashboard_json
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "dashboard_uid": result['uid'],
                    "dashboard_url": f"{self.grafana_url}/d/{result['uid']}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Grafana API error: {response.status_code}"
                }
    
    def _create_cpu_temperature_panel(self, server_id: int):
        """创建CPU温度面板"""
        return {
            "title": "CPU温度",
            "type": "timeseries",
            "datasource": "Prometheus",
            "targets": [
                {
                    "expr": f'ipmi_temperature_celsius{{server_id="{server_id}",name=~".*CPU.*"}}',
                    "legendFormat": "{{name}}",
                    "refId": "A"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": "celsius",
                    "min": 0,
                    "max": 100
                }
            }
        }
```

### 4.2 前端Grafana集成
```tsx
// src/components/monitoring/GrafanaPanel.tsx
const GrafanaPanel: React.FC<GrafanaPanelProps> = ({
  dashboardUid,
  panelId,
  title,
  height = 400
}) => {
  const [embedUrl, setEmbedUrl] = useState<string>('');
  const grafanaUrl = process.env.REACT_APP_GRAFANA_URL || 'http://localhost:3001';
  
  useEffect(() => {
    const params = new URLSearchParams({
      orgId: '1',
      refresh: '30s',
      kiosk: 'tv'
    });
    
    if (panelId) {
      setEmbedUrl(`${grafanaUrl}/d-solo/${dashboardUid}?panelId=${panelId}&${params}`);
    } else {
      setEmbedUrl(`${grafanaUrl}/d/${dashboardUid}?${params}`);
    }
  }, [dashboardUid, panelId, grafanaUrl]);

  return (
    <Card title={title} style={{ height: '100%' }}>
      <iframe
        src={embedUrl}
        width="100%"
        height="100%"
        frameBorder="0"
        style={{ minHeight: `${height}px` }}
      />
    </Card>
  );
};
```

## 5. 应用集成设计

### 5.1 服务器监控服务
```python
# app/services/server_monitoring.py
class ServerMonitoringService:
    """服务器监控服务，处理服务器变更时的监控配置同步"""
    
    def __init__(self, db: Session):
        self.db = db
        self.prometheus_manager = PrometheusConfigManager()
        self.grafana_service = GrafanaService(
            settings.GRAFANA_URL,
            settings.GRAFANA_API_KEY
        )
    
    async def on_server_added(self, server: Server) -> bool:
        """服务器添加时的监控配置处理"""
        try:
            # 1. 同步Prometheus目标配置
            servers = self.db.query(Server).filter(Server.monitoring_enabled == True).all()
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            # 2. 为新服务器创建Grafana仪表板
            if server.monitoring_enabled:
                await self.grafana_service.create_server_dashboard(server)
            
            logger.info(f"服务器 {server.id} 监控配置已更新")
            return True
        except Exception as e:
            logger.error(f"服务器 {server.id} 监控配置更新失败: {e}")
            return False
    
    async def on_server_deleted(self, server_id: int) -> bool:
        """服务器删除时的监控配置处理"""
        try:
            # 1. 同步Prometheus目标配置
            servers = self.db.query(Server).filter(
                Server.monitoring_enabled == True,
                Server.id != server_id
            ).all()
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            # 2. 删除对应的Grafana仪表板（可选）
            # 这里可以添加删除仪表板的逻辑
            
            logger.info(f"服务器 {server_id} 监控配置已清理")
            return True
        except Exception as e:
            logger.error(f"服务器 {server_id} 监控配置清理失败: {e}")
            return False
    
    async def on_server_updated(self, server: Server) -> bool:
        """服务器更新时的监控配置处理"""
        try:
            # 如果监控状态发生变化，则同步配置
            servers = self.db.query(Server).filter(Server.monitoring_enabled == True).all()
            await self.prometheus_manager.sync_ipmi_targets(servers)
            
            # 如果启用了监控且没有仪表板，则创建仪表板
            if server.monitoring_enabled:
                await self.grafana_service.create_server_dashboard(server)
            
            logger.info(f"服务器 {server.id} 监控配置已同步")
            return True
        except Exception as e:
            logger.error(f"服务器 {server.id} 监控配置同步失败: {e}")
            return False
```

### 5.2 Docker Compose 配置
```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.47.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/rules:/etc/prometheus/rules
      - ./monitoring/prometheus/targets:/etc/prometheus/targets
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=90d'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    restart: unless-stopped

  grafana:
    image: grafana/grafana-enterprise:10.1.0
    container_name: grafana
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
```