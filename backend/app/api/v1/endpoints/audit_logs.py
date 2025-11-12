from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from io import StringIO, BytesIO
import csv
import json

from app.core.database import get_db
from app.services.auth import AuthService
from app.schemas.audit_log import AuditLogListResponse, AuditLog
from app.services.audit_log import AuditLogService
from app.models.user import UserRole
from app.models.audit_log import AuditLog as AuditLogModel, AuditAction, AuditStatus, AuditAction, AuditStatus

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

router = APIRouter()

@router.get("/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action: str = Query(None),
    operator_id: int = Query(None),
    resource_type: str = Query(None),
    resource_id: int = Query(None),
    start_date: str = Query(None),  # ISO格式日期
    end_date: str = Query(None),    # ISO格式日期
    current_user = Depends(AuthService.get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    获取审计日志列表
    
    仅管理员用户可以访问。
    
    查询参数:
    - skip: 跳过的记录数 (默认0)
    - limit: 返回的记录数 (默认100, 最大1000)
    - action: 操作类型过滤 (可选)
    - operator_id: 操作者ID过滤 (可选)
    - resource_type: 资源类型过滤 (可选)
    - resource_id: 资源ID过滤 (可选)
    - start_date: 开始日期 (ISO格式, 如2025-01-01, 可选)
    - end_date: 结束日期 (ISO格式, 如2025-01-31, 可选)
    """
    
    audit_service = AuditLogService(db)
    
    # 解析日期
    start_datetime = None
    end_datetime = None
    
    try:
        if start_date:
            start_datetime = datetime.fromisoformat(start_date)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的日期格式: {str(e)}"
        )
    
    # 转换action为枚举值
    audit_action = None
    if action:
        try:
            audit_action = AuditAction(action.lower())
        except ValueError:
            # 如果action不是有效的枚举值，保持为None（不过滤）
            audit_action = None
    
    logs, total = audit_service.get_logs(
        skip=skip,
        limit=limit,
        action=audit_action,
        operator_id=operator_id,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_datetime,
        end_date=end_datetime,
    )
    
    return AuditLogListResponse(
        items=[
            AuditLog.model_validate(log) for log in logs
        ],
        total=total,
        skip=skip,
        limit=limit,
    )

@router.get("/audit-logs/{log_id}", response_model=AuditLog)
async def get_audit_log(
    log_id: int,
    current_user = Depends(AuthService.get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    获取指定ID的审计日志详情
    
    仅管理员用户可以访问。
    """
    
    audit_service = AuditLogService(db)
    log = audit_service.get_log_by_id(log_id)
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审计日志不存在"
        )
    
    return AuditLog.model_validate(log)

@router.get("/audit-logs/stats/summary")
async def get_audit_stats_summary(
    days: int = Query(7, ge=1, le=90),
    current_user = Depends(AuthService.get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    获取审计日志统计摘要
    
    返回过去N天内的操作统计信息。
    
    仅管理员用户可以访问。
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.audit_log import AuditLog
    
    start_date = datetime.now() - timedelta(days=days)
    
    # 统计各操作类型的数量
    action_stats = db.query(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.created_at >= start_date
    ).group_by(
        AuditLog.action
    ).all()
    
    # 统计各操作者的活动
    operator_stats = db.query(
        AuditLog.operator_username,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.created_at >= start_date
    ).group_by(
        AuditLog.operator_username
    ).all()
    
    # 统计失败操作
    failed_count = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= start_date,
        AuditLog.status == 'failed'
    ).scalar()
    
    # 总操作数
    total_count = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= start_date
    ).scalar()
    
    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": datetime.now().isoformat(),
        "total_operations": total_count,
        "failed_operations": failed_count,
        "success_rate": ((total_count - failed_count) / total_count * 100) if total_count > 0 else 0,
        "actions_breakdown": [
            {
                "action": str(action),
                "count": count
            }
            for action, count in action_stats
        ],
        "top_operators": [
            {
                "username": username,
                "count": count
            }
            for username, count in operator_stats
        ][:10],  # 只返回前10个
    }

@router.get("/export/csv")
async def export_audit_logs_csv(
    skip: int = Query(0, ge=0),
    limit: int = Query(10000, ge=1, le=100000),
    action: str = Query(None),
    operator_id: int = Query(None),
    resource_type: str = Query(None),
    resource_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    http_request: Request = None,
    current_user = Depends(AuthService.get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    导出审计日志为CSV格式
    
    仅管理员用户可以访问。
    """
    # ... 最乘的导出代码 ...
    # 在返回之前记录导出操作
    audit_service = AuditLogService(db)
    audit_service.create_log(
        action=AuditAction.AUDIT_LOG_EXPORT,
        operator_id=current_user.id,
        operator_username=current_user.username,
        resource_type="audit_log",
        action_details={
            "export_format": "csv",
            "skip": skip,
            "limit": limit,
            "filters": {
                "action": action,
                "operator_id": operator_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "start_date": start_date,
                "end_date": end_date
            }
        },
        result={"status": "success", "format": "csv"},
        ip_address=http_request.client.host if http_request and http_request.client else "unknown",
        user_agent=http_request.headers.get("user-agent", "unknown") if http_request else "unknown",
        status=AuditStatus.SUCCESS,
    )
    audit_service = AuditLogService(db)
    
    # 解析日期
    start_datetime = None
    end_datetime = None
    
    try:
        if start_date:
            start_datetime = datetime.fromisoformat(start_date)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的日期格式: {str(e)}"
        )
    
    # 转换action为枚举值
    audit_action = None
    if action:
        try:
            audit_action = AuditAction(action.lower())
        except ValueError:
            # 如果action不是有效的枚举值，保持为None（不过滤）
            audit_action = None
    
    logs, total = audit_service.get_logs(
        skip=skip,
        limit=limit,
        action=audit_action,
        operator_id=operator_id,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_datetime,
        end_date=end_datetime,
    )
    
    # 生成CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    headers = [
        'ID', '操作类型', '状态', '操作者ID', '操作者用户名',
        '资源类型', '资源ID', '资源名称', '操作详情', '操作结果',
        '错误消息', 'IP地址', 'User Agent', '创建时间'
    ]
    writer.writerow(headers)
    
    # 写入数据
    for log in logs:
        writer.writerow([
            log.id,
            log.action,
            log.status,
            log.operator_id,
            log.operator_username,
            log.resource_type,
            log.resource_id,
            log.resource_name,
            log.action_details,
            log.result,
            log.error_message,
            log.ip_address,
            log.user_agent,
            log.created_at,
        ])
    
    # 返回CSV文件流
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=audit_logs.csv"
        }
    )

@router.get("/export/excel")
async def export_audit_logs_excel(
    skip: int = Query(0, ge=0),
    limit: int = Query(10000, ge=1, le=100000),
    action: str = Query(None),
    operator_id: int = Query(None),
    resource_type: str = Query(None),
    resource_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    http_request: Request = None,
    current_user = Depends(AuthService.get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    导出审计日志为Excel格式
    
    仅管理员用户可以访问。
    """
    if not HAS_OPENPYXL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Excel导出功能不可用，请安装openpyxl库"
        )
    
    # ... 最乘的导出代码 ...
    # 在返回之前记录导出操作
    audit_service = AuditLogService(db)
    audit_service.create_log(
        action=AuditAction.AUDIT_LOG_EXPORT,
        operator_id=current_user.id,
        operator_username=current_user.username,
        resource_type="audit_log",
        action_details={
            "export_format": "excel",
            "skip": skip,
            "limit": limit,
            "filters": {
                "action": action,
                "operator_id": operator_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "start_date": start_date,
                "end_date": end_date
            }
        },
        result={"status": "success", "format": "excel"},
        ip_address=http_request.client.host if http_request and http_request.client else "unknown",
        user_agent=http_request.headers.get("user-agent", "unknown") if http_request else "unknown",
        status=AuditStatus.SUCCESS,
    )
    
    audit_service = AuditLogService(db)
    
    # 解析日期
    start_datetime = None
    end_datetime = None
    
    try:
        if start_date:
            start_datetime = datetime.fromisoformat(start_date)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的日期格式: {str(e)}"
        )
    
    # 转换action为枚举值
    audit_action = None
    if action:
        try:
            audit_action = AuditAction(action.lower())
        except ValueError:
            # 如果action不是有效的枚举值，保持为None（不过滤）
            audit_action = None
    
    logs, total = audit_service.get_logs(
        skip=skip,
        limit=limit,
        action=audit_action,
        operator_id=operator_id,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_datetime,
        end_date=end_datetime,
    )
    
    # 生成Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "审计日志"
    
    # 设置表头
    headers = [
        'ID', '操作类型', '状态', '操作者ID', '操作者用户名',
        '资源类型', '资源ID', '资源名称', '操作详情', '操作结果',
        '错误消息', 'IP地址', 'User Agent', '创建时间'
    ]
    
    # 设置表头样式
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # 设置列宽
    ws.column_dimensions['A'].width = 8  # ID
    ws.column_dimensions['B'].width = 15  # 操作类型
    ws.column_dimensions['C'].width = 10  # 状态
    ws.column_dimensions['D'].width = 10  # 操作者ID
    ws.column_dimensions['E'].width = 15  # 操作者用户名
    ws.column_dimensions['F'].width = 12  # 资源类型
    ws.column_dimensions['G'].width = 10  # 资源ID
    ws.column_dimensions['H'].width = 15  # 资源名称
    ws.column_dimensions['I'].width = 20  # 操作详情
    ws.column_dimensions['J'].width = 20  # 操作结果
    ws.column_dimensions['K'].width = 20  # 错误消息
    ws.column_dimensions['L'].width = 15  # IP地址
    ws.column_dimensions['M'].width = 20  # User Agent
    ws.column_dimensions['N'].width = 20  # 创建时间
    
    # 写入数据
    for row_idx, log in enumerate(logs, 2):
        ws.cell(row=row_idx, column=1).value = log.id
        ws.cell(row=row_idx, column=2).value = str(log.action)
        ws.cell(row=row_idx, column=3).value = log.status
        ws.cell(row=row_idx, column=4).value = log.operator_id
        ws.cell(row=row_idx, column=5).value = log.operator_username
        ws.cell(row=row_idx, column=6).value = log.resource_type
        ws.cell(row=row_idx, column=7).value = log.resource_id
        ws.cell(row=row_idx, column=8).value = log.resource_name
        ws.cell(row=row_idx, column=9).value = log.action_details
        ws.cell(row=row_idx, column=10).value = log.result
        ws.cell(row=row_idx, column=11).value = log.error_message
        ws.cell(row=row_idx, column=12).value = log.ip_address
        ws.cell(row=row_idx, column=13).value = log.user_agent
        ws.cell(row=row_idx, column=14).value = str(log.created_at) if log.created_at else ""
    
    # 保存到BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=audit_logs.xlsx"
        }
    )

@router.post("/cleanup")
async def cleanup_old_audit_logs(
    request_body: dict,
    http_request: Request,
    current_user = Depends(AuthService.get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    清理过旧的审计日志
    
    删除指定天数之前的日志记录。
    
    请求体:
    - days: 要清理的天数（删除该天数之前的日志），必须大于0
    
    仅管理员用户可以访问。
    """
    days = request_body.get('days') if isinstance(request_body, dict) else None
    
    if days is None or days <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days参数必须为正整数"
        )
    
    # 计算清理的截断日期
    cutoff_date = datetime.now() - timedelta(days=days)
    
    try:
        # 查询要删除的日志数量
        delete_count = db.query(AuditLogModel).filter(
            AuditLogModel.created_at < cutoff_date
        ).delete()
        
        db.commit()
        
        # 记录清理审计日志的操作
        audit_service = AuditLogService(db)
        audit_service.create_log(
            action=AuditAction.AUDIT_LOG_CLEANUP,
            operator_id=current_user.id,
            operator_username=current_user.username,
            resource_type="audit_log",
            action_details={
                "days": days,
                "cutoff_date": cutoff_date.isoformat()
            },
            result={
                "deleted_count": delete_count,
                "message": f"成功删除{delete_count}条{cutoff_date.strftime('%Y-%m-%d')}之前的审计日志"
            },
            ip_address=http_request.client.host if http_request.client else "unknown",
            user_agent=http_request.headers.get("user-agent", "unknown"),
            status=AuditStatus.SUCCESS,
        )
        
        return {
            "deleted_count": delete_count,
            "message": f"成功删除{delete_count}条{cutoff_date.strftime('%Y-%m-%d')}之前的审计日志"
        }
    except Exception as e:
        db.rollback()
        
        # 记录清理失败的操作
        try:
            audit_service = AuditLogService(db)
            audit_service.create_log(
                action=AuditAction.AUDIT_LOG_CLEANUP,
                operator_id=current_user.id,
                operator_username=current_user.username,
                resource_type="audit_log",
                action_details={
                    "days": days,
                    "cutoff_date": cutoff_date.isoformat()
                },
                error_message=str(e),
                ip_address=http_request.client.host if http_request.client else "unknown",
                user_agent=http_request.headers.get("user-agent", "unknown"),
                status=AuditStatus.FAILED,
            )
        except Exception as audit_error:
            logger.warning(f"记录清理审计日志失败操作失败: {str(audit_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理审计日志失败: {str(e)}"
        )
