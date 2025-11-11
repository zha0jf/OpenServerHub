import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.schemas.server import (
    NetworkScanRequest, NetworkScanResponse, DiscoveredDevice,
    BatchImportRequest, BatchImportResponse,
    CSVImportRequest, CSVImportResponse
)
from app.services.discovery import DiscoveryService
from app.services.auth import AuthService
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/network-scan", response_model=NetworkScanResponse)
async def scan_network(
    request: NetworkScanRequest,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
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
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """
    批量导入发现的服务器设备
    """
    try:
        logger.info(f"用户 {current_user.username} 发起批量导入: {len(request.devices)}台设备")
        
        discovery_service = DiscoveryService(db)
        
        # 执行批量导入
        result = await discovery_service.batch_import_servers(
            discovered_devices=request.devices,
            default_username=request.default_username,
            default_password=request.default_password,
            group_id=request.group_id
        )
        
        response = BatchImportResponse(**result)
        
        logger.info(f"批量导入完成: 成功{result['success_count']}台，失败{result['failed_count']}台")
        return response
        
    except ValidationError as e:
        logger.warning(f"批量导入参数验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"批量导入失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量导入失败，请稍后重试")

@router.post("/csv-import", response_model=CSVImportResponse)
async def import_from_csv(
    csv_file: UploadFile = File(...),
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
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
        
        # 执行CSV导入
        result = discovery_service.import_from_csv(
            csv_content=csv_text,
            group_id=group_id
        )
        
        response = CSVImportResponse(**result)
        
        logger.info(f"CSV导入完成: 成功{result['success_count']}台，失败{result['failed_count']}台")
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

@router.post("/csv-import-text", response_model=CSVImportResponse)
async def import_from_csv_text(
    request: CSVImportRequest,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """
    从CSV文本内容导入服务器（用于前端直接提交CSV内容）
    """
    try:
        logger.info(f"用户 {current_user.username} 通过文本导入CSV数据")
        
        discovery_service = DiscoveryService(db)
        
        # 执行CSV导入
        result = discovery_service.import_from_csv(
            csv_content=request.csv_content,
            group_id=request.group_id
        )
        
        response = CSVImportResponse(**result)
        
        logger.info(f"CSV文本导入完成: 成功{result['success_count']}台，失败{result['failed_count']}台")
        return response
        
    except ValidationError as e:
        logger.warning(f"CSV文本导入参数验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"CSV文本导入失败: {str(e)}")
        raise HTTPException(status_code=500, detail="CSV导入失败，请检查数据格式或稍后重试")

@router.get("/csv-template", response_class=PlainTextResponse)
async def get_csv_template(
    current_user = Depends(AuthService.get_current_user)
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
    current_user = Depends(AuthService.get_current_user)
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