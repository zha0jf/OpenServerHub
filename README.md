# OpenServerHub

OpenServerHub 是一个现代化的服务器管理平台，基于 FastAPI + React 技术栈开发，提供服务器 IPMI 控制、监控告警和集群管理功能。

## 功能特性

### 当前开发进度 🚧

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

#### Week 5-6 当前进行中 🚧
- ✅ 服务器分组管理
- [ ] 批量电源操作
- [ ] IP范围扫描发现设备
- [ ] CSV批量导入服务器

#### Week 7-8 监控集成 (下一阶段) 🔄
- [ ] Prometheus + IPMI Exporter 集成
- [ ] AlertManager 告警系统
- [ ] Grafana 可视化仪表板

## 技术栈

### 后端
- **Framework**: FastAPI
- **Database**: SQLite (开发) / PostgreSQL (生产)
- **ORM**: SQLAlchemy (不再使用Alembic迁移)
- **Authentication**: JWT
- **IPMI**: pyghmi
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
- Git

### 后端启动

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 复制环境配置
cp .env.example .env

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

### 访问应用

- 前端地址: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

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
└── docs/                   # 项目文档
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

#### 前端验收 ✅ 已完成
- ✅ React 应用正常启动
- ✅ 用户登录/登出功能
- ✅ 权限路由控制
- ✅ 服务器管理界面
- ✅ 用户管理界面
- ✅ 基础监控展示
- ✅ 响应式设计适配

#### 整体验收 ✅ 已完成
- ✅ 前后端正常通信
- ✅ 用户认证流程完整
- ✅ 服务器管理功能完整
- ✅ 一键启动脚本正常工作

### Week 5-6 集群管理 (当前进行中) 🚧
- ✅ 服务器分组功能
- [ ] 批量操作功能
- [ ] 设备发现功能

### 待开发功能 (下一阶段)
- [ ] Prometheus + Grafana 集成
- [ ] 告警通知系统
- [ ] 性能优化和压力测试

## 开发计划

### 当前阶段: Week 5-6 集群管理与批量操作 (进行中)
- [x] 服务器分组管理
- [ ] 批量电源控制
- [ ] IP范围设备发现
- [ ] CSV批量导入

### 下一阶段: Week 7-8 监控系统集成
- [ ] Prometheus 时序数据库
- [ ] IPMI Exporter 部署
- [ ] Grafana 可视化仪表板
- [ ] AlertManager 告警系统

### Week 3-4 计划 (已完成 ✅)  
- [x] 服务器集群管理
- [x] 基础IPMI操作功能
- [x] 用户管理系统

### Week 5-6 计划 (未来规划)
- [ ] 性能优化和压力测试
- [ ] Docker 容器化部署
- [ ] 产品化部署文档

## 注意事项

### 开发进度说明
- **当前状态**: 项目已完成Week 1-4的所有核心功能，进度超出预期
- **测试状态**: 所有已实现功能都已经过基础功能测试
- **部署就绪**: 可以使用 `start.bat` 一键启动，支持快速体验

### 环境配置
1. **开发环境**: 当前使用 SQLite 数据库，生产环境建议使用 PostgreSQL
2. **IPMI 测试**: 需要真实的服务器设备或 IPMI 模拟器进行测试
3. **安全配置**: 生产环境请修改默认密钥和密码
4. **端口配置**: 前端默认3000端口，后端默认8000端口

### 技术说明
5. **数据库迁移**: 已移除Alembic迁移工具，用于init_db.py直接创建表结构
6. **服务器字段**: 已移除hostname字段，现在只使用name和ipmi_ip进行服务器标识
7. **错误处理**: 已实现全局错误处理和统一日志系统
8. **监控系统**: 当前为基础监控实现，Prometheus+Grafana集成将在后续版本中完成

### 验收测试
9. **快速启动**: 请使用 `start.bat` 脚本进行完整测试，确保所有功能正常工作
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