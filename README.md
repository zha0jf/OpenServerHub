# OpenServerHub

OpenServerHub 是一个现代化的服务器管理平台，基于 FastAPI + React 技术栈开发，提供服务器 IPMI 控制、监控告警和集群管理功能。

## 功能特性

### 当前开发进度 ✅

#### Week 1-4 已完成功能 ✅

**后端功能**
- ✅ FastAPI 项目结构
- ✅ SQLite 数据库集成（开发环境）
- ✅ JWT 用户认证系统
- ✅ 用户角色权限管理 (Admin/Operator/User/ReadOnly)
- ✅ 服务器 CRUD 管理
- ✅ IPMI 连接池管理（最大50连接）
- ✅ 电源控制功能（开机/关机/重启）
- ✅ 服务器状态监控
- ✅ 监控数据采集和存储
- ✅ RESTful API 接口
- ✅ 自动 API 文档生成
- ✅ 全局异常处理和日志
- ✅ 数据库备份管理功能

**前端功能**
- ✅ React + TypeScript + Ant Design
- ✅ 用户认证和权限路由
- ✅ 响应式布局设计
- ✅ 仪表板总览
- ✅ 服务器管理界面
- ✅ 用户管理界面
- ✅ 监控数据展示
- ✅ 电源控制操作
- ✅ 服务器状态实时刷新
- ✅ 数据库备份管理界面

#### Week 5-6 集群管理功能 ✅
- ✅ 服务器分组管理
- ✅ 批量电源操作
- ✅ IP范围扫描发现设备
- ✅ CSV批量导入服务器

#### Week 7-8 监控集成 (已完成) ✅
- ✅ Prometheus + IPMI Exporter 集成
- ✅ AlertManager 告警系统
- ✅ Grafana 可视化仪表板
- ✅ 动态监控配置管理
- ✅ 数据库备份管理功能

#### Week 14-16 待开发功能
- 🔲 SOL (Serial Over LAN) 串口访问功能
- 🔲 用户体验优化
- 🔲 部署文档完善

## 技术栈

### 后端
- **Framework**: FastAPI
- **Database**: SQLite (开发和生产)
- **ORM**: SQLAlchemy (不再使用Alembic迁移)
- **Authentication**: JWT
- **IPMI**: pyghmi
- **Monitoring**: Prometheus + IPMI Exporter + Grafana + AlertManager
- **Language**: Python 3.9+

### 前端
- **Framework**: React 18
- **Language**: TypeScript
- **UI Library**: Ant Design
- **Router**: React Router
- **HTTP Client**: Axios

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+
- Docker & Docker Compose (用于监控系统)
- Git

### 后端启动

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 复制环境配置
cp scripts/env.example .env

# 初始化数据库（会创建默认管理员和测试数据）
python init_db.py

# 启动开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

### 监控系统启动

```bash
# 启动监控系统组件
docker-compose -f docker-compose.monitoring.yml up -d

# 查看监控系统状态
docker-compose -f docker-compose.monitoring.yml ps
```

### 开发监控环境启动

```bash
# 进入docker目录
cd docker

# 启动开发监控环境（集成后端、前端和监控组件）
docker-compose -f docker-compose.dev.single.yml up -d

# 或使用启动脚本（Windows）
start-dev-single.bat

# 或使用启动脚本（Linux/macOS）
./start-dev-single.sh
```

### 生产环境部署 (SQLite版本)

OpenServerHub支持使用SQLite数据库的生产环境部署，适用于小型部署场景。

```bash
# 进入docker目录
cd docker

# 启动生产环境（SQLite版本）
docker-compose -f docker-compose.prod.sqlite.yml --env-file .env.prod up -d

# 或使用启动脚本（Windows）
start-prod-sqlite.bat

# 或使用启动脚本（Linux/macOS）
./start-prod-sqlite.sh
```

首次部署时，请先复制并修改环境配置文件：

```bash
# 复制环境配置示例
cp .env.prod.example .env.prod

# 编辑环境配置文件，特别注意修改SECRET_KEY等安全配置
vim .env.prod
```

### 访问应用

- 前端地址: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- AlertManager: http://localhost:9093
- Grafana: http://localhost:3001

### 开发监控环境访问

开发监控环境已集成到单容器开发环境中，可通过以下地址访问：

- 前端开发服务器: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001
- AlertManager: http://localhost:9093
- IPMI Exporter: http://localhost:9290

### 默认账号和测试数据

- 用户名: `admin`
- 密码: `admin123`
- 测试服务器分组: "测试环境"
- 测试服务器: "测试服务器01" (IPMI: 192.168.1.100)

## 项目结构

```
OpenServerHub/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic模式
│   │   └── services/       # 业务逻辑
│   ├── main.py            # 应用入口
│   ├── init_db.py         # 数据库初始化
│   └── requirements.txt   # 依赖管理
├── frontend/               # 前端代码
│   ├── public/
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── contexts/       # 上下文
│   │   ├── pages/          # 页面
│   │   ├── services/       # API服务
│   │   └── types/          # 类型定义
│   └── package.json
├── monitoring/             # 监控系统配置
│   ├── prometheus/         # Prometheus配置
│   ├── alertmanager/       # AlertManager配置
│   ├── grafana/            # Grafana配置
│   └── ipmi-exporter/      # IPMI Exporter配置
├── docs/                   # 项目文档
│   ├── design/             # 设计文档
│   │   ├── 01-project-overview.md
│   │   ├── 02-system-architecture.md
│   │   ├── 03-technology-stack.md
│   │   ├── 04-database-design.md
│   │   ├── 05-api-design.md
│   │   ├── 07-sol-design.md
│   │   └── monitoring/     # 监控系统设计文档
│   ├── development/        # 开发文档
│   ├── deployment/         # 部署文档
│   ├── management/         # 项目管理文档
│   ├── troubleshooting/    # 故障排除文档
│   └── user/               # 用户文档
├── scripts/                # 启动脚本和环境配置
│   ├── start.bat          # Windows启动脚本
│   ├── start.sh           # Linux/macOS启动脚本
│   └── env.example        # 环境配置示例文件
└── docker-compose.monitoring.yml  # 监控系统Docker编排
```

## API 接口

### 认证接口
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/logout` - 用户登出
- `GET /api/v1/auth/me` - 获取当前用户

### 用户管理
- `GET /api/v1/users` - 获取用户列表
- `POST /api/v1/users` - 创建用户
- `PUT /api/v1/users/{id}` - 更新用户
- `DELETE /api/v1/users/{id}` - 删除用户

### 服务器管理
- `GET /api/v1/servers` - 获取服务器列表
- `POST /api/v1/servers` - 添加服务器
- `PUT /api/v1/servers/{id}` - 更新服务器
- `DELETE /api/v1/servers/{id}` - 删除服务器
- `POST /api/v1/servers/{id}/power/{action}` - 电源控制
- `POST /api/v1/servers/{id}/status` - 更新服务器状态

### 监控接口
- `GET /api/v1/monitoring/servers/{id}/metrics` - 获取监控数据
- `POST /api/v1/monitoring/servers/{id}/collect` - 手动采集数据
- `GET /api/v1/monitoring/prometheus/query` - 查询Prometheus数据
- `GET /api/v1/monitoring/prometheus/query_range` - 查询Prometheus数据范围

### 告警接口
- `POST /api/v1/monitoring/alerts/webhook` - AlertManager告警Webhook

### 数据库备份接口
- `POST /api/v1/backup/create` - 创建数据库备份
- `GET /api/v1/backup/list` - 获取备份文件列表
- `DELETE /api/v1/backup/delete` - 删除备份文件
- `POST /api/v1/backup/restore` - 恢复数据库备份
- `POST /api/v1/backup/verify` - 验证备份文件完整性
- `GET /api/v1/backup/download/{filename}` - 下载备份文件

## 开发进度验收状态

### Week 1-4 验收标准 ✅ 全部完成

#### 后端验收 ✅ 已完成
- ✅ FastAPI 服务正常启动
- ✅ 数据库连接和初始化正常
- ✅ JWT 认证功能正常
- ✅ 服务器 CRUD 操作正常
- ✅ 电源控制功能工作
- ✅ API 文档自动生成
- ✅ 用户管理CRUD功能
- ✅ 监控数据采集API
- ✅ 数据库备份管理API

#### 前端验收 ✅ 已完成
- ✅ React 应用正常启动
- ✅ 用户登录/登出功能
- ✅ 权限路由控制
- ✅ 服务器管理界面
- ✅ 用户管理界面
- ✅ 基础监控展示
- ✅ 响应式设计适配
- ✅ 数据库备份管理界面

#### 整体验收 ✅ 已完成
- ✅ 前后端正常通信
- ✅ 用户认证流程完整
- ✅ 服务器管理功能完整
- ✅ 一键启动脚本正常工作
- ✅ 数据库备份功能完整

### Week 5-6 集群管理 ✅ 已完成
- ✅ 服务器分组功能
- ✅ 批量操作功能
- ✅ 设备发现功能
- ✅ CSV批量导入

### Week 7-8 监控系统集成 ✅ 已完成
- ✅ Prometheus 时序数据库
- ✅ IPMI Exporter 部署
- ✅ Grafana 可视化仪表板
- ✅ AlertManager 告警系统
- ✅ 动态监控配置管理

### 故障排除
- [监控系统故障排除指南](docs/troubleshooting/monitoring-troubleshooting-guide.md) - 常见问题诊断和解决方法

### 待开发功能 (下一阶段)
- [ ] 性能优化和压力测试
- [ ] Docker 容器化部署
- [ ] 产品化部署文档

## 开发计划

### 当前阶段: Week 9-10 性能优化
- [ ] 监控数据查询优化
- [ ] 大规模服务器监控性能测试
- [ ] 告警规则优化

### 下一阶段: Week 11-12 性能优化
- [ ] 数据库查询优化
- [ ] IPMI操作并发控制
- [ ] 缓存策略实现

### Week 3-4 计划 (已完成 ✅)  
- [x] 服务器集群管理
- [x] 基础IPMI操作功能
- [x] 用户管理系统

### Week 5-6 计划 (已完成 ✅)
- [x] 服务器分组管理
- [x] 批量电源控制
- [x] IP范围设备发现
- [x] CSV批量导入

## 监控系统架构

### 组件说明
1. **IPMI Exporter**: 独立容器运行，通过IPMI协议从服务器BMC采集硬件传感器数据
2. **Prometheus**: 时序数据库，定期从IPMI Exporter拉取监控指标并存储
3. **AlertManager**: 处理Prometheus发送的告警，支持邮件、Webhook等通知方式
4. **Grafana**: 监控数据可视化展示，提供丰富的仪表板和图表
5. **FastAPI后端**: 提供监控数据查询API，管理监控配置，处理告警回调
6. **React前端**: 展示监控数据和仪表板，提供用户交互界面

### 动态配置管理
- 服务器添加/删除时自动更新Prometheus监控目标
- 为新服务器自动创建Grafana仪表板
- 支持服务器监控配置的动态调整

## 监控系统文档

### 用户文档
- [监控系统用户指南](docs/user/monitoring/01-user-guide.md) - 面向最终用户的操作指南
- [监控系统管理员手册](docs/user/monitoring/02-admin-guide.md) - 面向系统管理员的部署和维护指南

#### 历史用户文档
- [监控系统用户手册](docs/user/monitoring-user-manual.md) - 面向最终用户的操作指南
- [监控系统使用指南](docs/user/monitoring-guide.md) - 详细的使用说明和最佳实践
- [监控系统用户故事](docs/user/monitoring-user-stories.md) - 用户使用场景和需求
- [监控系统最佳实践](docs/user/monitoring-best-practices.md) - 监控系统使用和维护的最佳实践
- [监控告警最佳实践](docs/user/monitoring-alerts-best-practices.md) - 监控告警配置和管理的最佳实践

### 管理员文档
- [监控系统管理员手册](docs/user/monitoring/02-admin-guide.md) - 面向系统管理员的部署和维护指南
- [监控系统部署指南](docs/design/monitoring/04-deployment.md) - 详细的部署步骤和配置说明

#### 历史管理员文档
- [监控系统管理员手册](docs/user/monitoring-admin-manual.md) - 面向系统管理员的部署和维护指南
- [监控系统部署指南](docs/deployment/03-monitoring-deployment.md) - 详细的部署步骤和配置说明
- [监控系统部署和运维指南](docs/deployment/monitoring-system-deployment-and-operations-guide.md) - 部署和运维指南
- [监控系统升级和维护指南](docs/deployment/monitoring-system-upgrade-maintenance-guide.md) - 系统升级和维护流程
- [监控系统性能调优指南](docs/deployment/monitoring-system-performance-tuning-guide.md) - 系统性能优化方法和最佳实践

### 开发文档
- [监控系统实现总结](docs/development/monitoring/01-implementation-summary.md) - 系统实现总结报告
- [监控系统综合测试报告](docs/development/monitoring/02-test-report.md) - 系统综合测试报告
- [监控系统文档优化报告](docs/development/monitoring/03-document-optimization-report.md) - 文档优化过程和结果

#### 历史开发文档
- [监控系统测试报告](docs/development/monitoring-system-test-report.md) - 系统测试过程和结果
- [监控系统综合测试报告](docs/development/monitoring-system-comprehensive-test-report.md) - 系统综合测试报告
- [监控系统实现总结](docs/development/monitoring-system-implementation-summary.md) - 系统实现总结报告
- [监控系统实现完整报告](docs/development/monitoring-system-implementation-complete-report.md) - 系统实现完整报告

### 设计文档
- [监控系统架构设计](docs/design/monitoring/01-architecture.md) - 系统整体架构设计
- [监控系统组件设计](docs/design/monitoring/02-components.md) - 核心组件详细设计
- [监控系统API设计](docs/design/monitoring/03-api.md) - API接口设计
- [监控系统部署指南](docs/design/monitoring/04-deployment.md) - 部署配置说明
- [监控系统告警设计](docs/design/monitoring/05-alerts.md) - 告警规则和处理机制
- [监控系统配置管理](docs/design/monitoring/06-configuration.md) - 动态配置管理机制

#### 历史设计文档
- [监控系统设计](docs/design/06-monitoring-system.md) - 监控系统基础设计
- [监控系统增强设计](docs/design/06-monitoring-system-enhanced.md) - 增强功能设计
- [监控系统最终设计](docs/design/08-monitoring-system-final.md) - 完整实现总结
- [监控系统完整设计](docs/design/09-monitoring-system-complete-design.md) - 完整设计文档
- [监控系统完整实现](docs/design/monitoring-system-complete-implementation.md) - 完整实现设计文档
- [监控系统完整实现设计](docs/design/monitoring-system-complete-implementation-design.md) - 完整实现设计文档
- [监控系统最终实现设计](docs/design/monitoring-system-final-implementation-design.md) - 最终实现设计文档
- [监控系统架构图](docs/design/monitoring-architecture-diagram.md) - 系统架构图
- [监控系统部署架构](docs/design/monitoring-deployment-architecture.md) - 部署架构
- [监控系统数据流](docs/design/monitoring-data-flow.md) - 数据流图
- [监控系统配置管理](docs/design/monitoring-configuration-management.md) - 配置管理
- [监控系统API设计](docs/design/monitoring-api-design.md) - API接口设计

## 注意事项

### 开发进度说明
- **当前状态**: 项目已完成Week 1-8的所有核心功能，进度超出预期
- **测试状态**: 所有已实现功能都已经过基础功能测试
- **部署就绪**: 可以使用 `start-prod-sqlite.bat` 一键启动，支持快速体验

### 环境配置
1. **开发环境**: 当前使用 SQLite 数据库，生产环境也使用 SQLite
2. **IPMI 测试**: 需要真实的服务器设备或 IPMI 模拟器进行测试
3. **安全配置**: 生产环境请修改默认密钥和密码
4. **端口配置**: 前端默认3000端口，后端默认8000端口，监控系统使用9090/9093/3001端口

### 技术说明
5. **数据库迁移**: 已移除Alembic迁移工具，用于init_db.py直接创建表结构
6. **服务器字段**: 已移除hostname字段，现在只使用name和ipmi_ip进行服务器标识
7. **错误处理**: 已实现全局错误处理和统一日志系统
8. **监控系统**: 已完成Prometheus+Grafana+AlertManager完整集成

### 验收测试
9. **快速启动**: 请使用 `start-prod-sqlite.bat` 脚本进行完整测试，确保所有功能正常工作
10. **默认账号**: admin / admin123 (生产环境请及时修改)
11. **功能测试**: 建议测试登录、服务器管理、用户管理、监控面板等核心功能

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

MIT License - 详见 LICENSE 文件

## 联系方式

- 项目地址: https://github.com/yourusername/OpenServerHub
- 问题反馈: https://github.com/yourusername/OpenServerHub/issues