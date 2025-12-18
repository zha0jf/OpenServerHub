import time
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import ValidationError
import logging
import ipaddress
import csv
import io

from app.core.database import get_async_db
from app.services.discovery import DiscoveryService
from app.services.server import ServerService
from app.services.auth import get_current_user
from app.services.audit_log import AuditLogService
from app.models.audit_log import AuditAction, AuditStatus
from app.schemas.server import (
    NetworkScanRequest, NetworkScanResponse, DiscoveredDevice,
    BatchImportRequest, BatchImportResponse, CSVImportRequest
)

router = APIRouter()
logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"]
    return request.client.host if request.client else "unknown"


@router.post("/network-scan", response_model=NetworkScanResponse)
async def scan_network(
    request: NetworkScanRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """
    网络范围扫描BMC设备
    
    支持的网络格式:
    - CIDR格式: 192.168.1.0/24
    - IP范围格式: 192.168.1.1-192.168.1.100
    - 单个IP: 192.168.1.100
    """
    try:
        logger.info(f"用户 {current_user.username} 发起网络扫描: {request.network}")
        
        discovery_service = DiscoveryService(db)
        audit_service = AuditLogService(db)
        start_time = time.time()
        
        # 执行网络扫描
        discovered_devices = await discovery_service.scan_network_range(
            network=request.network,
            port=request.port,
            timeout=request.timeout,
            max_workers=request.max_workers
        )
        
        scan_duration = time.time() - start_time
        
        # 计算扫描的IP总数
        # TODO: 应该在DiscoveryService中提供一个公共方法来计算IP数量，而不是直接调用内部方法
        total_scanned = len(discovery_service._parse_network_range(request.network))
        
        # 转换为响应格式
        devices = [
            DiscoveredDevice(**device) for device in discovered_devices
        ]
        
        response = NetworkScanResponse(
            total_scanned=total_scanned,
            devices_found=len(devices),
            devices=devices,
            scan_duration=round(scan_duration, 2)
        )
        
        logger.info(f"网络扫描完成: 扫描{total_scanned}个IP，发现{len(devices)}个设备，耗时{scan_duration:.2f}秒")
        
        # 记录扫描操作
        await audit_service.log_discovery_operation(
            user_id=current_user.id,
            username=current_user.username,
            action=AuditAction.DISCOVERY_START,
            action_details={
                "network": request.network,
                "port": request.port,
                "timeout": request.timeout,
                "max_workers": request.max_workers,
                "total_scanned": total_scanned,
                "devices_found": len(devices),
                "scan_duration": round(scan_duration, 2)
            },
            ip_address=get_client_ip(http_request) if http_request else "unknown",
            user_agent=http_request.headers.get("user-agent", "unknown") if http_request else "unknown",
            success=True,
        )
        
        return response
        
    except ValidationError as e:
        logger.warning(f"网络扫描参数验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"网络扫描失败: {str(e)}")
        raise HTTPException(status_code=500, detail="网络扫描失败，请检查网络配置或稍后重试")


@router.post("/batch-import", response_model=BatchImportResponse)
async def batch_import_servers(
    request: BatchImportRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """
    批量导入发现的服务器设备
    """
    try:
        logger.info(f"用户 {current_user.username} 发起批量导入: {len(request.devices)}台设备")
        
        discovery_service = DiscoveryService(db)
        audit_service = AuditLogService(db)
        
        # 执行批量导入
        result = await discovery_service.batch_import_servers(
            discovered_devices=request.devices,
            default_username=request.default_username,
            default_password=request.default_password,
            group_id=request.group_id
        )
        
        response = BatchImportResponse(**result)
        
        logger.info(f"批量导入完成: 成功{result['success_count']}台，失败{result['failed_count']}台")
        
        # 记录批量导入操作
        await audit_service.log_discovery_operation(
            user_id=current_user.id,
            username=current_user.username,
            action=AuditAction.DISCOVERY_COMPLETE,
            action_details={
                "devices_count": len(request.devices),
                "group_id": request.group_id,
                "total_count": result['total_count'],
                "success_count": result['success_count'],
                "failed_count": result['failed_count']
            },
            ip_address=get_client_ip(http_request) if http_request else "unknown",
            user_agent=http_request.headers.get("user-agent", "unknown") if http_request else "unknown",
            success=result['failed_count'] == 0,
        )
        
        return response
        
    except ValidationError as e:
        logger.warning(f"批量导入参数验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"批量导入失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量导入失败，请稍后重试")


@router.post("/csv-import", response_model=BatchImportResponse)
async def import_from_csv(
    csv_file: UploadFile = File(...),
    group_id: Optional[int] = None,
    http_request: Request = None,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """
    从CSV文件导入服务器
    
    CSV文件格式要求：
    name,ipmi_ip,ipmi_username,ipmi_password,ipmi_port,manufacturer,model,serial_number,description
    """
    try:
        # 验证文件类型
        if not csv_file.filename.endswith('.csv'):
            raise ValidationError("请上传CSV格式的文件")
        
        # 读取文件内容
        csv_content = await csv_file.read()
        csv_text = csv_content.decode('utf-8')
        
        logger.info(f"用户 {current_user.username} 上传CSV文件: {csv_file.filename}")
        
        discovery_service = DiscoveryService(db)
        audit_service = AuditLogService(db)
        
        # 执行CSV导入
        result = await discovery_service.import_from_csv(
            csv_content=csv_text,
            group_id=group_id
        )
        
        response = BatchImportResponse(**result)
        
        logger.info(f"CSV导入完成: 成功{result['success_count']}台，失败{result['failed_count']}台")
        
        # 记录CSV导入操作
        if http_request:
            await audit_service.log_discovery_operation(
                user_id=current_user.id,
                username=current_user.username,
                action=AuditAction.SERVER_IMPORT,
                action_details={
                    "filename": csv_file.filename,
                    "import_type": "csv_file",
                    "group_id": group_id,
                    "total_count": result['total_count'],
                    "success_count": result['success_count'],
                    "failed_count": result['failed_count']
                },
                ip_address=get_client_ip(http_request),
                user_agent=http_request.headers.get("user-agent", "unknown"),
                success=True,
            )
        
        return response
        
    except ValidationError as e:
        logger.warning(f"CSV导入参数验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except UnicodeDecodeError:
        logger.warning("CSV文件编码错误")
        raise HTTPException(status_code=400, detail="CSV文件编码格式不正确，请使用UTF-8编码")
    except Exception as e:
        logger.error(f"CSV导入失败: {str(e)}")
        raise HTTPException(status_code=500, detail="CSV导入失败，请检查文件格式或稍后重试")


@router.post("/csv-import-text", response_model=BatchImportResponse)
async def import_from_csv_text(
    request: CSVImportRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """
    从CSV文本内容导入服务器（用于前端直接提交CSV内容）
    """
    try:
        logger.info(f"用户 {current_user.username} 通过文本导入CSV数据")
        
        discovery_service = DiscoveryService(db)
        audit_service = AuditLogService(db)
        
        # 执行CSV导入
        result = await discovery_service.import_from_csv(
            csv_content=request.csv_content,
            group_id=request.group_id
        )
        
        response = BatchImportResponse(**result)
        
        logger.info(f"CSV文本导入完成: 成功{result['success_count']}台，失败{result['failed_count']}台")
        
        # 记录CSV文本导入操作
        await audit_service.log_discovery_operation(
            user_id=current_user.id,
            username=current_user.username,
            action=AuditAction.SERVER_IMPORT,
            action_details={
                "import_type": "csv_text",
                "group_id": request.group_id,
                "lines": len(request.csv_content.splitlines()),
                "total_count": result['total_count'],
                "success_count": result['success_count'],
                "failed_count": result['failed_count']
            },
            ip_address=get_client_ip(http_request) if http_request else "unknown",
            user_agent=http_request.headers.get("user-agent", "unknown") if http_request else "unknown",
            success=result['failed_count'] == 0,
        )
        
        return response
        
    except ValidationError as e:
        logger.warning(f"CSV文本导入参数验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"CSV文本导入失败: {str(e)}")
        raise HTTPException(status_code=500, detail="CSV导入失败，请检查数据格式或稍后重试")


@router.get("/csv-template", response_class=PlainTextResponse)
async def get_csv_template(
    current_user = Depends(get_current_user)
):
    """
    获取CSV导入模板
    """
    try:
        discovery_service = DiscoveryService(None)  # 不需要数据库连接
        template = discovery_service.generate_csv_template()
        
        return PlainTextResponse(
            content=template,
            headers={
                "Content-Disposition": "attachment; filename=server_import_template.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
    except Exception as e:
        logger.error(f"生成CSV模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成CSV模板失败")


@router.get("/network-examples")
async def get_network_examples(
    current_user = Depends(get_current_user)
):
    """
    获取网络范围格式示例
    """
    examples = {
        "cidr_examples": [
            "192.168.1.0/24",
            "10.0.0.0/24", 
            "172.16.1.0/24"
        ],
        "range_examples": [
            "192.168.1.1-192.168.1.100",
            "10.0.0.10-10.0.0.50",
            "172.16.1.100-172.16.1.200"
        ],
        "single_ip_examples": [
            "192.168.1.100",
            "10.0.0.10",
            "172.16.1.100",
            "192.168.1.100,192.168.1.101",
            "10.0.0.10,10.0.0.11,10.0.0.12"
        ],
        "description": {
            "cidr": "CIDR格式：网络地址/子网掩码位数，如 192.168.1.0/24 表示扫描 192.168.1.1-192.168.1.254",
            "range": "范围格式：起始IP-结束IP，如 192.168.1.1-192.168.1.100",
            "single": "逗号分隔示例：输入一个或多个用逗号分隔的IP地址"
        }
    }
    
    return examples
