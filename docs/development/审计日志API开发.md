# 审计日志API开发指南

## 概述

本文档详细说明审计日志功能的API设计、实现方式和集成方法。

## 新增组件

### 1. 数据模型 (`app/models/audit_log.py`)

#### AuditLog
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: 日志ID (主键)
    action: 操作类型 (AuditAction枚举)
    status: 操作状态 (success/failed/partial)
    operator_id: 操作者用户ID (可为空)
    operator_username: 操作者用户名 (可为空)
    resource_type: 资源类型 (user/server/group等)
    resource_id: 资源ID (可为空)
    resource_name: 资源名称 (可为空)
    action_details: 操作参数 (JSON文本)
    result: 操作结果 (JSON文本)
    error_message: 错误信息 (可为空)
    ip_address: 客户端IP (IPv4/IPv6)
    user_agent: User Agent (可为空)
    created_at: 创建时间 (自动生成)
```

#### AuditAction 枚举
包含35个操作类型：
- 用户认证: LOGIN, LOGOUT, LOGIN_FAILED
- 用户管理: USER_CREATE, USER_UPDATE, USER_DELETE, USER_ROLE_CHANGE
- 服务器管理: SERVER_CREATE, SERVER_UPDATE, SERVER_DELETE, SERVER_IMPORT
- 电源控制: POWER_ON, POWER_OFF, POWER_RESTART, POWER_FORCE_OFF, POWER_FORCE_RESTART
- LED控制: LED_ON, LED_OFF
- 批量操作: BATCH_POWER_CONTROL, BATCH_GROUP_CHANGE
- 监控相关: MONITORING_ENABLE, MONITORING_DISABLE
- 设备发现: DISCOVERY_START, DISCOVERY_COMPLETE
- 组管理: GROUP_CREATE, GROUP_UPDATE, GROUP_DELETE

#### AuditStatus 枚举
- SUCCESS: 操作成功
- FAILED: 操作失败
- PARTIAL: 批量操作部分成功

### 2. 审计日志服务 (`app/services/audit_log.py`)

#### AuditLogService 类

**主要方法:**

##### create_log()
```python
def create_log(
    action: AuditAction,
    operator_id: Optional[int] = None,
    operator_username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    resource_name: Optional[str] = None,
    action_details: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: AuditStatus = AuditStatus.SUCCESS,
) -> AuditLog:
```
创建审计日志记录

##### get_logs()
```python
def get_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[AuditAction] = None,
    operator_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> tuple[list[AuditLog], int]:
```
查询审计日志，支持多条件过滤

##### 专用日志方法

###### log_login()
```python
def log_login(
    username: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    user_id: Optional[int] = None,
    success: bool = True,
) -> AuditLog:
```
记录登录操作

###### log_power_control()
```python
def log_power_control(
    user_id: int,
    username: str,
    server_id: int,
    server_name: str,
    action_type: str,
    success: bool = True,
    error_message: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
```
记录电源控制操作

### 3. API 接口 (`app/api/v1/endpoints/audit_logs.py`)

#### 获取审计日志列表
```
GET /api/v1/audit-logs
```

**查询参数:**
```
skip: int = 0              # 分页偏移
limit: int = 100           # 每页数量 (1-1000)
action: str = None         # 操作类型过滤
operator_id: int = None    # 操作者ID过滤
resource_type: str = None  # 资源类型过滤
resource_id: int = None    # 资源ID过滤
start_date: str = None     # 开始日期 (ISO格式)
end_date: str = None       # 结束日期 (ISO格式)
```

**返回示例:**
```json
{
  "items": [
    {
      "id": 1,
      "action": "LOGIN",
      "status": "success",
      "operator_id": 1,
      "operator_username": "admin",
      "resource_type": "user",
      "resource_id": 1,
      "resource_name": "admin",
      "action_details": null,
      "result": null,
      "error_message": null,
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2025-01-12T10:22:08"
    }
  ],
  "total": 100,
  "skip": 0,
  "limit": 100
}
```

#### 获取日志详情
```
GET /api/v1/audit-logs/{log_id}
```

**返回:** 单条AuditLog记录

#### 获取统计摘要
```
GET /api/v1/audit-logs/stats/summary?days=7
```

**返回:**
```json
{
  "period_days": 7,
  "start_date": "2025-01-05T00:00:00",
  "end_date": "2025-01-12T15:30:00",
  "total_operations": 25,
  "failed_operations": 2,
  "success_rate": 92.0,
  "actions_breakdown": [
    {"action": "LOGIN", "count": 10},
    {"action": "POWER_ON", "count": 8}
  ],
  "top_operators": [
    {"username": "admin", "count": 20}
  ]
}
```

#### 导出审计日志为CSV
```
GET /api/v1/audit-logs/export/csv
```

**查询参数:**
- 支持所有列表查询参数
- `skip`, `limit`, `action`, `operator_id`, `resource_type`, `resource_id`, `start_date`, `end_date`

**返回:**
- CSV格式文件流
- Content-Type: `text/csv; charset=utf-8`
- Content-Disposition: `attachment; filename=audit_logs.csv`

#### 导出审计日志为Excel
```
GET /api/v1/audit-logs/export/excel
```

**查询参数:**
- 支持所有列表查询参数
- `skip`, `limit`, `action`, `operator_id`, `resource_type`, `resource_id`, `start_date`, `end_date`

**返回:**
- Excel格式文件流
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Content-Disposition: `attachment; filename=audit_logs.xlsx`
- 包含美化样式 (表头颜色、列宽等)

#### 清理过期审计日志
```
POST /api/v1/audit-logs/cleanup
```

**请求体:**
```json
{
  "days": 30
}
```

**返回:**
```json
{
  "deleted_count": 150,
  "message": "成功删除150条2025-01-12之前的审计日志"
}
```

## 集成指南

### 在登录模块集成

```python
from app.services.audit_log import AuditLogService

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request,
    db: Session = Depends(get_db)
):
    audit_service = AuditLogService(db)
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent")
    
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        # 记录失败的登录
        audit_service.log_login(
            username=form_data.username,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False
        )
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 记录成功的登录
    audit_service.log_login(
        username=user.username,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        success=True
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
```

### 在电源控制模块集成

```python
from app.services.audit_log import AuditLogService

@router.post("/{server_id}/power/{action}")
async def power_control(
    server_id: int,
    action: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    server_service = ServerService(db)
    audit_service = AuditLogService(db)
    
    server = server_service.get_server(server_id)
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent")
    
    try:
        result = await server_service.power_control(server_id, action)
        
        # 记录成功的操作
        audit_service.log_power_control(
            user_id=current_user.id,
            username=current_user.username,
            server_id=server_id,
            server_name=server.name,
            action_type=action,
            success=True,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        
        return result
    except Exception as e:
        # 记录失败的操作
        audit_service.log_power_control(
            user_id=current_user.id,
            username=current_user.username,
            server_id=server_id,
            server_name=server.name,
            action_type=action,
            success=False,
            error_message=str(e),
            ip_address=client_ip,
            user_agent=user_agent,
        )
        raise
```

### 在其他模块集成

```python
from app.services.audit_log import AuditLogService
from app.models.audit_log import AuditAction

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_admin_user)
):
    user_service = UserService(db)
    audit_service = AuditLogService(db)
    
    try:
        new_user = user_service.create_user(user_data)
        
        # 记录成功的用户创建
        audit_service.log_user_operation(
            operator_id=current_user.id,
            operator_username=current_user.username,
            action=AuditAction.USER_CREATE,
            target_user_id=new_user.id,
            target_username=new_user.username,
            action_details={"email": new_user.email, "role": new_user.role},
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        
        return new_user
    except Exception as e:
        # 记录失败的操作
        audit_service.log_user_operation(
            operator_id=current_user.id,
            operator_username=current_user.username,
            action=AuditAction.USER_CREATE,
            action_details={"email": user_data.email},
            success=False,
            error_message=str(e),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        raise
```

## 数据库迁移

迁移脚本: `backend/alembic/versions/0003_add_audit_logs_table.py`

创建 `audit_logs` 表并添加以下索引:
- `ix_audit_logs_action`
- `ix_audit_logs_operator_id`
- `ix_audit_logs_resource_type`
- `ix_audit_logs_resource_id`
- `ix_audit_logs_created_at`

运行迁移:
```bash
cd backend
python init_db.py
```

## 权限和安全

- **权限**: 仅 Admin 用户可访问审计日志API
- **认证**: 需要有效的JWT令牌
- **脱敏**: 不记录敏感信息（密码、令牌等）
- **追踪**: 记录客户端IP和User Agent

## 最佳实践

1. **总是记录关键操作**
   - 用户认证/授权相关操作
   - 系统配置变更
   - 权限变更
   - 数据修改

2. **提供足够的上下文**
   - 记录操作的详细参数
   - 记录操作结果或错误信息
   - 记录受影响的资源

3. **异常处理**
   - 在成功和失败情况下都记录
   - 捕获异常时记录错误信息
   - 不让审计日志错误中断主业务

4. **性能考虑**
   - 使用分页查询大量数据
   - 定期清理过期日志
   - 监控日志表大小

## 常见问题

**Q: 如何查询特定用户的所有操作?**
A: `GET /api/v1/audit-logs?operator_id=1`

**Q: 如何查询特定日期范围的操作?**
A: `GET /api/v1/audit-logs?start_date=2025-01-10&end_date=2025-01-12`

**Q: 如何导出审计日志?**
A: 可以使用专门的导出端点:
- CSV格式: `GET /api/v1/audit-logs/export/csv`
- Excel格式: `GET /api/v1/audit-logs/export/excel`

也支持在客户端通过标准API查询然后处理导出

**Q: 日志会一直保存吗?**
A: 是的，无自动清理。建议定期备份和清理过期日志

**Q: 性能影响有多大?**
A: 轻微，日志写入不阻塞主逻辑。数据库有优化索引
