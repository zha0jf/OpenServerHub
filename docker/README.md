# OpenServerHub Docker 部署指南

## 快速开始

### 1. 环境要求
- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 内存
- 10GB 可用磁盘空间

### 2. 配置环境变量

根据您要启动的环境类型，需要配置相应的环境变量文件：

#### 生产环境
```bash
cd docker
cp .env.prod.example .env.prod
# 编辑 .env.prod 文件，修改必要的配置，特别是 SECRET_KEY
```

#### 开发环境
```bash
cd docker
cp .env.dev.example .env.dev
# 编辑 .env.dev 文件，修改必要的配置
```

### 3. 启动服务

您可以选择直接使用Docker Compose命令启动服务，也可以使用我们提供的启动脚本来启动服务。

#### 方法一：使用启动脚本（推荐）

##### 生产环境
```bash
# Windows
start-prod-sqlite.bat

# Linux/macOS
./start-prod-sqlite.sh
```

##### 开发环境
```bash
# Windows
start-dev-single.bat

# Linux/macOS
./start-dev-single.sh
```

#### 方法二：使用Docker Compose命令

##### 生产环境
```bash
# 1. 复制环境配置文件
# Linux/macOS
cp .env.prod.example .env.prod
# Windows
copy .env.prod.example .env.prod

# 2. 编辑 .env.prod 文件，修改必要的配置，特别是 SECRET_KEY

# 3. 启动服务
docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod up -d
```

##### 开发环境
```bash
# 1. 复制环境配置文件
# Linux/macOS
cp .env.dev.example .env.dev
# Windows
copy .env.dev.example .env.dev

# 2. 编辑 .env.dev 文件，修改必要的配置

# 3. 启动服务
docker-compose -f docker-compose.dev.single.yml --env-file .env.dev up -d
```

开发环境已集成到单容器配置中，包含了后端服务、前端服务以及完整的监控组件（Prometheus、Grafana、AlertManager和IPMI Exporter）。这个环境特别适合在开发过程中进行监控功能的测试和调试。

#### 监控环境
```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### 4. 访问服务

根据您启动的环境类型，服务访问地址会有所不同：

#### 生产环境
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001
- AlertManager: http://localhost:9093

#### 开发环境
- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001
- AlertManager: http://localhost:9093
- IPMI Exporter: http://localhost:9290

## 服务说明

### 包含的服务

#### 生产环境
- **Backend**: FastAPI后端服务（使用SQLite数据库）
- **Prometheus**: 监控数据收集和存储
- **Grafana**: 监控数据可视化
- **AlertManager**: 告警管理
- **IPMI Exporter**: 硬件监控数据采集

#### 开发环境
- **Backend**: FastAPI后端服务（使用SQLite数据库）
- **Frontend**: React前端应用
- **Prometheus**: 监控数据收集和存储
- **Grafana**: 监控数据可视化
- **AlertManager**: 告警管理
- **IPMI Exporter**: 硬件监控数据采集

#### 监控环境
- **Prometheus**: 监控数据收集和存储
- **Grafana**: 监控数据可视化
- **AlertManager**: 告警管理
- **IPMI Exporter**: 硬件监控数据采集

### 端口映射

#### 生产环境
- 8000: 后端API
- 9090: Prometheus
- 3001: Grafana
- 9093: AlertManager
- 9290: IPMI Exporter

#### 开发环境
- 3000: 前端开发服务器
- 8000: 后端API
- 9090: Prometheus
- 3001: Grafana
- 9093: AlertManager
- 9290: IPMI Exporter

在开发监控环境中，所有服务都在同一个Docker网络中运行，因此它们可以相互访问。例如，Prometheus可以直接通过服务名访问后端API和IPMI Exporter。

## 常用命令

### 查看日志
```bash
docker-compose logs -f [service_name]
```

### 停止服务
```bash
docker-compose down
```

### 重新构建
```bash
docker-compose build --no-cache
```

### 数据备份
```bash
docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod exec backend cp /app/data/openserverhub.db /app/data/backup.db
docker cp openserverhub-backend-prod:/app/data/backup.db ./backup.db
```

### 数据恢复
```bash
docker cp ./backup.db openserverhub-backend-prod:/app/data/openserverhub.db
```

### 使用启动脚本进行备份和恢复
您也可以使用启动脚本来进行备份和恢复操作。启动脚本提供了更友好的交互界面和更多的选项。

```bash
# Windows
start-prod-sqlite.bat

# Linux/macOS
./start-prod-sqlite.sh
```

## 配置说明

### 环境变量

#### 通用配置
- `DATABASE_URL`: 数据库连接字符串
- `SECRET_KEY`: JWT密钥（生产环境必须修改为强密钥）
- `ENVIRONMENT`: 运行环境
- `DEBUG`: 调试模式
- `LOG_LEVEL`: 日志级别
- `CORS_ORIGINS`: CORS允许的源

#### IPMI配置
- `IPMI_CONNECTION_POOL_SIZE`: IPMI连接池大小
- `IPMI_TIMEOUT`: IPMI超时时间
- `IPMI_RETRY_COUNT`: IPMI重试次数

#### 监控配置
- `MONITORING_ENABLED`: 是否启用监控
- `MONITORING_INTERVAL`: 监控间隔（秒）
- `PROMETHEUS_URL`: Prometheus服务地址
- `GRAFANA_URL`: Grafana服务地址
- `GRAFANA_API_KEY`: Grafana API密钥

#### 定时任务配置
- `POWER_STATE_REFRESH_INTERVAL`: 电源状态刷新间隔（分钟）
- `POWER_STATE_REFRESH_ENABLED`: 是否启用电源状态刷新
- `SCHEDULER_ENABLED`: 是否启用定时任务

### 数据持久化

#### 生产环境
- SQLite数据: `./backend/data`目录（通过Docker卷持久化）
- 应用数据: `./backend/data`目录（通过Docker卷持久化）
- 日志文件: `./backend/logs`目录（通过Docker卷持久化）

#### 开发环境
- SQLite数据: `./backend/data`目录（通过Docker卷持久化）
- 应用数据: `./backend/data`目录（通过Docker卷持久化）

## 安全建议

1. **修改默认密码**: 在生产环境中修改所有默认密码
2. **使用HTTPS**: 配置SSL证书
3. **限制访问**: 使用防火墙限制数据库访问
4. **定期备份**: 设置自动备份策略
5. **监控**: 启用监控和告警

## 故障排查

### 服务无法启动
1. 检查端口是否被占用
2. 查看Docker日志: `docker-compose logs`
3. 确保环境变量配置正确

### 数据库连接失败
1. 检查数据库服务状态（开发和生产环境均为SQLite）
2. 验证数据库连接字符串
3. 检查网络连通性（生产环境）

### 前端无法访问
1. 检查前端开发服务器状态
2. 验证前端构建是否成功
3. 检查端口映射

## 性能优化

### 数据库优化
- 定期执行VACUUM
- 创建适当的索引
- 配置连接池

### 缓存优化
- 配置Redis内存限制
- 使用合适的过期策略
- 监控缓存命中率

### 前端优化
- 启用Gzip压缩
- 配置CDN
- 优化构建配置