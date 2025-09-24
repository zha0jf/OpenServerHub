# 监控系统架构设计

## 1. 概述

本文档详细描述 OpenServerHub 监控系统的整体架构设计，包括组件职责、数据流向和集成方式。

## 2. 设计目标

1. 集成 Prometheus 时序数据库进行监控数据存储
2. 使用 IPMI Exporter 独立容器进行硬件数据采集
3. 实现监控目标的动态管理（添加/删除服务器时自动更新）
4. 集成 AlertManager 告警系统
5. 实现 Grafana 可视化集成
6. 提供完整的监控数据查询和展示 API

## 3. 系统架构

### 3.1 整体架构图

```mermaid
graph TB
    subgraph "服务器硬件层"
        BMC1[服务器1 BMC]
        BMC2[服务器2 BMC] 
        BMC3[服务器N BMC]
    end
    
    subgraph "数据采集层"
        IPMI1[IPMI Exporter 1]
        IPMI2[IPMI Exporter 2]
        IPMI3[IPMI Exporter N]
    end
    
    subgraph "监控存储层"
        Prometheus[Prometheus Server]
        TSDB[(时序数据库)]
    end
    
    subgraph "告警处理层"
        AlertManager[AlertManager]
        Rules[告警规则引擎]
    end
    
    subgraph "可视化层"
        Grafana[Grafana Server]
        Dashboard[监控仪表板]
    end
    
    subgraph "应用集成层"
        API[FastAPI后端]
        WebUI[React前端]
    end
    
    BMC1 --> IPMI1
    BMC2 --> IPMI2
    BMC3 --> IPMI3
    
    IPMI1 --> Prometheus
    IPMI2 --> Prometheus
    IPMI3 --> Prometheus
    
    Prometheus --> TSDB
    Prometheus --> Rules
    Rules --> AlertManager
    
    Prometheus --> Grafana
    Grafana --> Dashboard
    
    API --> Prometheus
    API --> Grafana
    WebUI --> API
    WebUI --> Dashboard
    AlertManager --> API
```

### 3.2 组件职责说明

| 组件 | 职责 |
|------|------|
| IPMI Exporter | 独立容器运行，通过 IPMI 协议从 BMC 采集硬件传感器数据 |
| Prometheus | 时序数据库，定期从 IPMI Exporter 拉取监控指标并存储 |
| AlertManager | 处理 Prometheus 发送的告警，支持邮件、Webhook 等通知方式 |
| Grafana | 监控数据可视化展示，提供丰富的仪表板和图表 |
| FastAPI 后端 | 提供监控数据查询 API，管理监控配置，处理告警回调 |
| React 前端 | 展示监控数据和仪表板，提供用户交互界面 |

## 4. 数据流向

### 4.1 监控数据采集流程

```mermaid
sequenceDiagram
    participant BMC as 服务器BMC
    participant Exporter as IPMI Exporter
    participant Prometheus as Prometheus
    participant Backend as FastAPI后端
    
    loop 每60秒
        Prometheus->>Exporter: 拉取指标请求
        Exporter->>BMC: IPMI查询传感器
        BMC-->>Exporter: 返回传感器数据
        Exporter-->>Prometheus: 返回格式化指标
        Prometheus->>Prometheus: 存储时序数据
    end
    
    Backend->>Prometheus: 查询监控数据
    Prometheus-->>Backend: 返回历史数据
    Backend->>Frontend: 提供API接口
```

### 4.2 告警处理流程

```mermaid
sequenceDiagram
    participant Prometheus as Prometheus
    participant AlertManager as AlertManager
    participant Backend as FastAPI后端
    participant User as 用户
    
    Prometheus->>AlertManager: 触发告警
    AlertManager->>AlertManager: 分组和去重
    AlertManager->>User: 发送邮件通知
    AlertManager->>Backend: 发送Webhook
    Backend->>Backend: 处理告警回调
    Backend->>Database: 记录告警历史
```

## 5. 部署架构

### 5.1 容器化部署

所有监控组件均采用容器化部署，通过 Docker Compose 进行统一编排管理。

### 5.2 网络架构

组件间通过内部网络进行通信，对外暴露必要的端口：
- Prometheus: 9090
- AlertManager: 9093
- Grafana: 3001

## 6. 安全设计

### 6.1 认证与授权
1. Prometheus API 访问需要认证
2. Grafana 集成使用 API Key
3. IPMI Exporter 使用独立的认证配置

### 6.2 网络安全
1. 限制 Prometheus 和 AlertManager 的网络访问
2. 使用 HTTPS 加密通信
3. IPMI Exporter 仅暴露必要的端口

### 6.3 数据保护
1. 敏感信息（如 IPMI 密码）加密存储
2. 监控数据备份策略
3. 访问日志记录和审计