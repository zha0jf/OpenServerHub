# OpenServerHub Docker 部署指南

## 快速开始

### 1. 环境要求
- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 内存
- 10GB 可用磁盘空间

### 2. 配置环境变量

```bash
cd docker
cp .env.example .env
# 编辑 .env 文件，修改必要的配置
```

### 3. 启动服务

#### 生产环境
```bash
docker-compose up -d
```

#### 开发环境
```bash
docker-compose -f docker-compose.dev.yml up -d
```

#### 监控环境
```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### 4. 访问服务
- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001
- AlertManager: http://localhost:9093

## 服务说明

### 包含的服务

#### 生产环境
- **PostgreSQL**: 主数据库
- **Redis**: 缓存和会话存储
- **Backend**: FastAPI后端服务
- **Frontend**: React前端应用
- **Nginx**: 反向代理和静态文件服务

#### 开发环境
- **Backend**: FastAPI后端服务（使用SQLite数据库）
- **Frontend**: React前端应用

#### 监控环境
- **Prometheus**: 监控数据收集和存储
- **Grafana**: 监控数据可视化
- **AlertManager**: 告警管理
- **IPMI Exporter**: 硬件监控数据采集

### 端口映射
- 3000: 前端开发服务器
- 8000: 后端API
- 5432: PostgreSQL（仅生产环境）
- 6379: Redis（仅生产环境）
- 80: Nginx（仅生产环境）
- 9090: Prometheus
- 3001: Grafana
- 9093: AlertManager
- 9290: IPMI Exporter

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
docker-compose exec postgres pg_dump -U postgres openserverhub > backup.sql
```

### 数据恢复
```bash
docker-compose exec -T postgres psql -U postgres openserverhub < backup.sql
```

## 配置说明

### 环境变量
- `DATABASE_URL`: 数据库连接字符串
- `REDIS_URL`: Redis连接字符串
- `SECRET_KEY`: JWT密钥
- `ENVIRONMENT`: 运行环境
- `DEBUG`: 调试模式
- `LOG_LEVEL`: 日志级别
- `CORS_ORIGINS`: CORS允许的源

### 数据持久化
- PostgreSQL数据: `postgres_data`卷
- 应用数据: `./backend/data`目录
- 日志文件: `./backend/logs`目录

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
1. 检查数据库服务状态（生产环境为PostgreSQL，开发环境为SQLite）
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