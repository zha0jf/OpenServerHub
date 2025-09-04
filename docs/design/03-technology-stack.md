# 技术选型说明

## 后端技术栈

### 1. Web框架 - FastAPI

**选择理由**:
- **高性能**: 基于Starlette和Pydantic，性能接近Node.js
- **现代化**: 原生支持async/await异步编程
- **自动文档**: 自动生成OpenAPI/Swagger文档
- **类型安全**: 完全支持Python类型提示
- **易于开发**: 简洁的API设计，学习曲线平缓

**主要特性**:
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="OpenServerHub API")

class ServerCreate(BaseModel):
    name: str
    bmc_ip: str
    username: str
    password: str

@app.post("/servers/")
async def create_server(server: ServerCreate):
    # 自动请求验证和响应序列化
    return {"message": "Server created"}
```

### 2. ORM - SQLAlchemy 2.0

**选择理由**:
- **成熟稳定**: Python生态最成熟的ORM
- **异步支持**: SQLAlchemy 2.0原生支持async/await
- **灵活性**: 支持多种数据库，SQL和ORM混用
- **性能优化**: 懒加载、连接池、查询优化

**使用示例**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

async def get_server_with_cluster(session: AsyncSession, server_id: int):
    stmt = select(Server).options(
        selectinload(Server.cluster)
    ).where(Server.id == server_id)
    
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

### 3. 数据库 - SQLite/PostgreSQL

**开发环境 - SQLite**:
- **零配置**: 无需独立数据库服务
- **轻量级**: 适合开发和测试
- **事务支持**: ACID特性完整

**生产环境 - PostgreSQL**:
- **高性能**: 支持复杂查询和大数据量
- **扩展性**: 丰富的插件生态
- **可靠性**: 久经考验的企业级数据库
- **JSON支持**: 适合存储配置和监控数据

### 4. IPMI库 - pyghmi

**选择理由**:
- **纯Python**: 无需额外系统依赖
- **协议完整**: 支持IPMI 2.0完整功能
- **异步支持**: 可以与FastAPI异步框架集成
- **跨平台**: 支持Linux、Windows、macOS

## 前端技术栈

### 1. 框架 - React 18

**选择理由**:
- **生态成熟**: 丰富的组件库和工具链
- **性能优秀**: 虚拟DOM和Concurrent Features
- **开发体验**: 热重载、DevTools支持
- **社区活跃**: 问题解决方案丰富

### 2. 语言 - TypeScript

**选择理由**:
- **类型安全**: 编译期错误检查
- **IDE支持**: 智能提示和重构
- **代码质量**: 提高代码可维护性
- **团队协作**: 接口定义明确

### 3. UI组件库 - Ant Design

**选择理由**:
- **组件丰富**: 覆盖企业级应用需求
- **设计语言**: 统一的视觉设计规范
- **TypeScript**: 原生TypeScript支持
- **国际化**: 内置多语言支持

## 监控技术栈

### 1. 时序数据库 - Prometheus

**选择理由**:
- **专业监控**: 专为监控设计的时序数据库
- **拉取模式**: 主动拉取，降低目标系统压力
- **PromQL**: 强大的查询语言
- **服务发现**: 自动发现监控目标

### 2. 数据采集 - IPMI Exporter

**选择理由**:
- **标准化**: Prometheus官方推荐
- **无侵入**: 通过IPMI接口采集，不影响系统
- **多厂商**: 支持Dell、HP、IBM等主流厂商
- **自动发现**: 可配置自动发现BMC设备

### 3. 可视化 - Grafana

**选择理由**:
- **专业仪表板**: 丰富的可视化组件
- **数据源集成**: 原生支持Prometheus
- **告警功能**: 内置告警和通知
- **权限管理**: 用户和组织管理

### 4. 告警管理 - AlertManager

**选择理由**:
- **智能路由**: 基于标签的告警路由
- **去重合并**: 避免告警风暴
- **多种通知**: 邮件、Slack、钉钉等
- **抑制规则**: 灵活的告警抑制

## 部署技术栈

### 1. 容器化 - Docker

**选择理由**:
- **环境一致**: 开发、测试、生产环境一致
- **快速部署**: 镜像打包，一键部署
- **资源隔离**: 容器隔离，互不影响
- **扩展性**: 支持水平扩展

### 2. 编排 - Docker Compose

**选择理由**:
- **简化部署**: 一键启动多个服务
- **网络管理**: 自动创建服务网络
- **存储管理**: 数据卷持久化
- **环境变量**: 灵活的配置管理

### 3. 多架构支持

**ARM64和X86架构同时支持**:
- 使用多阶段构建
- 交叉编译配置
- 平台特定优化

## 缓存技术选型

### 1. 应用缓存 - 内存缓存

**选择理由**:
- **简化部署**: 无需额外服务
- **低延迟**: 内存访问速度快
- **开发简单**: Python字典实现
- **资源控制**: 可控的内存使用

### 2. 缓存策略

**分层缓存设计**:
- **用户会话缓存**: 1小时TTL
- **服务器状态缓存**: 30秒TTL  
- **IPMI连接缓存**: 5分钟TTL
- **传感器数据缓存**: 10秒TTL

## 安全技术选型

### 1. 认证 - JWT

**选择理由**:
- **无状态**: 服务器不需要存储会话
- **标准化**: RFC 7519标准
- **跨域支持**: 适合前后端分离
- **负载均衡**: 支持多实例部署

### 2. 权限控制 - RBAC

**角色定义**:
- **超级管理员**: 所有权限
- **系统管理员**: 服务器管理权限
- **运维人员**: 监控和基本操作权限
- **只读用户**: 查看权限

## 性能优化技术

### 1. 异步编程

**FastAPI异步支持**:
- 原生async/await
- 并发处理能力
- 非阻塞I/O操作

### 2. 连接池管理

**数据库连接池**:
- SQLAlchemy连接池
- IPMI连接复用
- 资源优化管理

### 3. 前端性能优化

**React优化策略**:
- 虚拟滚动处理大列表
- React.memo防止重渲染
- 懒加载和代码分割
- 组件优化和缓存