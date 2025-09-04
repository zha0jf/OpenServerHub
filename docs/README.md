# OpenServerHub 开发文档

## 📚 文档导航

### 设计文档 (Design Documents)
- [项目概览](./design/01-project-overview.md) - 项目介绍、功能特性、适用场景
- [系统架构设计](./design/02-system-architecture.md) - 微服务架构、数据流、安全设计
- [技术选型说明](./design/03-technology-stack.md) - 技术栈详细说明和选择理由
- [数据库设计](./design/04-database-design.md) - 数据模型、表结构、索引设计
- [API接口设计](./design/05-api-design.md) - REST API接口规范
- [监控系统设计](./design/06-monitoring-system.md) - Prometheus + Grafana 监控方案

### 开发指南 (Development Guides)
- [开发环境搭建](./development/01-environment-setup.md) - 开发环境配置指南
- [后端开发指南](./development/02-backend-guide.md) - FastAPI后端开发规范
- [前端开发指南](./development/03-frontend-guide.md) - React前端开发规范
- [代码规范](./development/04-coding-standards.md) - 代码风格和质量标准
- [测试指南](./development/05-testing-guide.md) - 单元测试和集成测试

### 部署运维 (Deployment & Operations)
- [Docker部署指南](./deployment/01-docker-deployment.md) - 容器化部署方案
- [生产环境配置](./deployment/02-production-config.md) - 生产环境配置指南
- [监控运维指南](./deployment/03-monitoring-ops.md) - 监控系统运维
- [备份恢复方案](./deployment/04-backup-recovery.md) - 数据备份和恢复
- [性能调优指南](./deployment/05-performance-tuning.md) - 系统性能优化

### 项目管理 (Project Management)
- [开发计划](./management/01-development-plan.md) - 分阶段开发计划和里程碑
- [版本发布计划](./management/02-release-plan.md) - 版本发布策略
- [质量保证计划](./management/03-quality-assurance.md) - 质量控制流程

### 用户文档 (User Documentation)
- [用户手册](./user/01-user-manual.md) - 系统使用指南
- [管理员手册](./user/02-admin-manual.md) - 系统管理指南
- [API文档](./user/03-api-reference.md) - API接口参考

### 故障排查 (Troubleshooting)
- [常见问题FAQ](./troubleshooting/01-faq.md) - 常见问题和解决方案
- [故障排查指南](./troubleshooting/02-troubleshooting-guide.md) - 系统故障诊断
- [错误代码参考](./troubleshooting/03-error-codes.md) - 错误代码说明

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- Git

### 快速部署

```bash
# 克隆项目
git clone https://github.com/yourusername/OpenServerHub.git
cd OpenServerHub

# 启动服务
docker-compose up -d

# 访问应用
# Web界面: http://localhost:3000
# API文档: http://localhost:8080/docs
# Grafana: http://localhost:3001
```

### 本地开发

```bash
# 后端开发
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端开发
cd frontend
npm install
npm start
```

## 项目结构

```
OpenServerHub/
├── backend/           # Python FastAPI 后端
├── frontend/          # React TypeScript 前端
├── monitoring/        # Prometheus + Grafana 配置
├── docs/             # 项目文档
├── scripts/          # 部署和工具脚本
├── docker-compose.yml
└── README.md
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

Apache License 2.0