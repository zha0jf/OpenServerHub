# 数据库设计

## 数据库选型

### 开发环境 - SQLite
- **文件数据库**: 零配置，适合开发和测试
- **ACID支持**: 完整的事务特性
- **轻量级**: 单文件部署，便于开发

### 生产环境 - PostgreSQL
- **高性能**: 支持复杂查询和大数据量
- **JSON支持**: 适合存储配置和元数据
- **扩展性**: 支持分区表和复制
- **可靠性**: 久经考验的企业级数据库

## 核心表结构设计

### 1. 用户管理模块

```sql
-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'operator', 'user', 'readonly')),
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户权限表
CREATE TABLE user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id)
);
```

### 2. 服务器管理模块

```sql
-- 集群表
CREATE TABLE clusters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    location VARCHAR(200),
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 服务器表
CREATE TABLE servers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    
    -- IPMI连接信息
    ipmi_ip INET NOT NULL,
    ipmi_port INTEGER DEFAULT 623,
    ipmi_username VARCHAR(50) NOT NULL,
    ipmi_password VARCHAR(255) NOT NULL, -- 加密存储
    
    -- 硬件信息
    manufacturer VARCHAR(50),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    
    -- 状态信息
    power_state VARCHAR(20) DEFAULT 'unknown' 
        CHECK (power_state IN ('on', 'off', 'unknown', 'error')),
    health_status VARCHAR(20) DEFAULT 'unknown' 
        CHECK (health_status IN ('ok', 'warning', 'critical', 'unknown')),
    
    -- 监控配置
    monitoring_enabled BOOLEAN DEFAULT true,
    monitoring_interval INTEGER DEFAULT 60,
    
    -- 关联关系
    cluster_id INTEGER REFERENCES clusters(id) ON DELETE SET NULL,
    
    -- 元数据和标签
    metadata JSONB DEFAULT '{}',
    tags VARCHAR(255)[],
    
    -- 审计字段
    is_active BOOLEAN DEFAULT true,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. 监控数据模块

```sql
-- 监控记录表（时序数据）
CREATE TABLE monitoring_records (
    id BIGSERIAL PRIMARY KEY,
    server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION,
    unit VARCHAR(20),
    status VARCHAR(20) DEFAULT 'ok' 
        CHECK (status IN ('ok', 'warning', 'critical', 'unknown')),
    sensor_name VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 告警记录表
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    alert_rule VARCHAR(100) NOT NULL,
    alert_level VARCHAR(20) NOT NULL 
        CHECK (alert_level IN ('info', 'warning', 'critical')),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    current_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    
    -- 状态管理
    status VARCHAR(20) DEFAULT 'firing' 
        CHECK (status IN ('firing', 'acknowledged', 'resolved')),
    fired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    
    metadata JSONB DEFAULT '{}'
);
```

### 4. 操作审计模块

```sql
-- 操作日志表
CREATE TABLE operation_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    operation VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INTEGER,
    resource_name VARCHAR(200),
    
    -- 操作详情
    details JSONB DEFAULT '{}',
    result VARCHAR(20) DEFAULT 'pending' 
        CHECK (result IN ('success', 'failed', 'pending', 'cancelled')),
    error_message TEXT,
    
    -- 请求信息
    ip_address INET,
    user_agent TEXT,
    
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

## 索引设计

### 主要索引

```sql
-- 用户表索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;

-- 服务器表索引
CREATE INDEX idx_servers_ipmi_ip ON servers(ipmi_ip);
CREATE INDEX idx_servers_cluster ON servers(cluster_id);
CREATE INDEX idx_servers_active ON servers(is_active) WHERE is_active = true;
CREATE INDEX idx_servers_power_state ON servers(power_state);

-- 监控记录表索引
CREATE INDEX idx_monitoring_server_time ON monitoring_records(server_id, timestamp DESC);
CREATE INDEX idx_monitoring_metric_time ON monitoring_records(metric_name, timestamp DESC);

-- 告警表索引
CREATE INDEX idx_alerts_server_status ON alerts(server_id, status);
CREATE INDEX idx_alerts_fired_at ON alerts(fired_at DESC);

-- 操作日志表索引
CREATE INDEX idx_operation_logs_user_time ON operation_logs(user_id, started_at DESC);
CREATE INDEX idx_operation_logs_time ON operation_logs(started_at DESC);
```

## 数据库约束和触发器

### 检查约束

```sql
-- 服务器表约束
ALTER TABLE servers ADD CONSTRAINT chk_bmc_port 
    CHECK (bmc_port > 0 AND bmc_port < 65536);

ALTER TABLE servers ADD CONSTRAINT chk_monitoring_interval 
    CHECK (monitoring_interval >= 10);
```

### 自动时间戳更新

```sql
-- 创建更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 应用到相关表
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_servers_updated_at 
    BEFORE UPDATE ON servers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## 数据分区策略

### 监控数据分区

```sql
-- 按月分区监控记录表
CREATE TABLE monitoring_records (
    -- 字段定义...
) PARTITION BY RANGE (timestamp);

-- 创建分区表
CREATE TABLE monitoring_records_y2024m01 PARTITION OF monitoring_records
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

## 性能优化

### 查询优化

```sql
-- 监控数据查询优化
SELECT metric_name, value, timestamp 
FROM monitoring_records 
WHERE server_id = 1 
  AND timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

### 连接池配置

```python
# SQLAlchemy连接池配置
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # 基础连接数
    max_overflow=30,        # 最大溢出连接
    pool_pre_ping=True,     # 连接健康检查
    pool_recycle=3600       # 连接回收时间
)
```

## 数据备份和清理策略

### 备份策略

```bash
# 数据库备份脚本
pg_dump -h localhost -U backup_user -d openshub \
        -f "/var/backups/postgresql/openshub_${DATE}.sql"
```

### 数据清理策略

```sql
-- 清理历史监控数据（保留90天）
DELETE FROM monitoring_records 
WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '90 days';

-- 清理已解决的告警（保留30天）
DELETE FROM alerts 
WHERE status = 'resolved' 
AND resolved_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
```