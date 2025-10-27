# Grafana监控界面无法访问问题解决方案

## 问题描述

在服务器10.10.0.1上使用start-dev-single.sh启动测试环境后，从10.10.0.232通过浏览器访问web界面时，监控界面中无法打开grafana监控界面，报错"10.10.0.1拒绝访问"。手动通过浏览器打开嵌入的grafana页面地址时，能打开页面但报错"Dashboard not found"。

## 问题分析

经过分析，问题主要由以下几个方面引起：

1. **仪表板UID不匹配**：前端代码使用了固定的仪表板UID格式，但后端创建的仪表板UID格式不一致
2. **网络访问配置问题**：CORS配置和网络访问设置不正确
3. **Grafana配置问题**：Grafana的域名和根URL配置不正确
4. **仪表板预配置缺失**：缺少默认的仪表板配置文件

## 解决方案

### 1. 修改前端代码以正确获取仪表板信息

修改文件：`frontend/src/pages/monitoring/MonitoringDashboard.tsx`

主要改动：
- 从后端API获取实际的仪表板UID，而不是使用固定的格式
- 添加了错误处理机制，当API调用失败时使用默认格式作为后备方案

### 2. 添加后端API端点获取仪表板信息

修改文件：`backend/app/api/v1/endpoints/monitoring.py`

添加了新的API端点 `/servers/{server_id}/dashboard`，用于获取服务器的Grafana仪表板信息。

### 3. 统一仪表板UID格式

修改文件：`backend/app/services/server_monitoring.py`

确保后端创建仪表板时使用与前端一致的UID格式：`server-dashboard-{server_id}`

### 4. 更新网络配置

修改文件：`docker/.env.dev.network` 和 `docker/start-dev-single.sh`

更新了以下配置：
- `SERVER_IP=10.10.0.1`
- `REACT_APP_GRAFANA_URL=http://10.10.0.1:3001`
- 添加了对10.10.0.232的CORS支持

### 5. 配置Grafana服务器设置

修改文件：`docker/docker-compose.dev.single.yml`

添加了Grafana服务器配置：
- `GF_SERVER_DOMAIN=10.10.0.1`
- `GF_SERVER_ROOT_URL=http://10.10.0.1:3001`

### 6. 添加默认仪表板配置

创建文件：
- `monitoring/grafana/provisioning/dashboards/default.yml`
- `monitoring/grafana/provisioning/dashboards/server-dashboard.json`

提供了默认的仪表板配置，确保即使API调用失败也能显示仪表板。

## 验证解决方案

1. 重新启动开发环境：
   ```bash
   cd docker
   ./start-dev-single.sh
   ```

2. 从10.10.0.232访问：
   - 前端：http://10.10.0.1:3000
   - Grafana：http://10.10.0.1:3001

3. 在前端监控页面选择服务器，查看图表视图是否正常显示。

## 预防措施

1. 确保前后端使用一致的仪表板UID格式
2. 正确配置网络和CORS设置
3. 为Grafana提供默认仪表板配置
4. 在API调用失败时提供合理的后备方案

## 结论

通过以上修改，解决了Grafana监控界面无法访问的问题。关键在于统一前后端的仪表板UID格式、正确配置网络访问参数以及提供默认的仪表板配置。