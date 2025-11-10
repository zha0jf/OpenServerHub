from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.schemas.server import ServerCreate, ServerUpdate, ServerResponse, ServerGroupCreate, ServerGroupResponse, BatchPowerRequest, BatchPowerResponse, ClusterStatsResponse
from app.services.server import ServerService
from app.services.auth import AuthService
from app.core.exceptions import ValidationError, IPMIError, NotFoundError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# 服务器管理
@router.post("/", response_model=ServerResponse)
async def create_server(
    server_data: ServerCreate,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """添加服务器"""
    try:
        server_service = ServerService(db)
        return server_service.create_server(server_data)
    except ValidationError as e:
        logger.warning(f"服务器创建验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"服务器创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器创建失败，请稍后重试")

@router.get("/", response_model=List[ServerResponse])
async def get_servers(
    skip: int = 0,
    limit: int = 100,
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取服务器列表"""
    server_service = ServerService(db)
    return server_service.get_servers(skip=skip, limit=limit, group_id=group_id)

# 集群统计接口（必须在 /{server_id} 之前）
@router.get("/stats", response_model=ClusterStatsResponse)
async def get_cluster_statistics(
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取集群统计信息"""
    try:
        server_service = ServerService(db)
        stats = server_service.get_cluster_statistics(group_id=group_id)
        
        return ClusterStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"获取集群统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")

@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取指定服务器"""
    server_service = ServerService(db)
    server = server_service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server

@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: int,
    server_data: ServerUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """更新服务器信息"""
    try:
        server_service = ServerService(db)
        server = server_service.update_server(server_id, server_data)
        if not server:
            raise HTTPException(status_code=404, detail="服务器不存在")
        return server
    except ValidationError as e:
        logger.warning(f"服务器更新验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except HTTPException:
        raise  # 重新抛出HTTPException
    except Exception as e:
        logger.error(f"服务器更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器更新失败，请稍后重试")

@router.delete("/{server_id}")
async def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """删除服务器"""
    server_service = ServerService(db)
    success = server_service.delete_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return {"message": "服务器删除成功"}

# 电源控制
@router.post("/{server_id}/power/{action}")
async def power_control(
    server_id: int,
    action: str,  # on, off, restart, force_off
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """服务器电源控制"""
    try:
        server_service = ServerService(db)
        result = await server_service.power_control(server_id, action)
        return result
    except ValidationError as e:
        logger.warning(f"电源控制验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except IPMIError as e:
        logger.error(f"IPMI电源控制失败: {e.message}")
        raise HTTPException(status_code=500, detail=f"IPMI操作失败: {e.message}")
    except Exception as e:
        logger.error(f"电源控制失败: {str(e)}")
        raise HTTPException(status_code=500, detail="电源控制失败，请稍后重试")

# 服务器状态更新
@router.post("/{server_id}/status")
async def update_server_status(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """更新服务器状态"""
    try:
        server_service = ServerService(db)
        result = await server_service.update_server_status(server_id)
        return result
    except ValidationError as e:
        logger.warning(f"状态更新验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except IPMIError as e:
        logger.warning(f"IPMI状态更新失败: {e.message}")
        raise HTTPException(status_code=500, detail=f"IPMI连接失败: {e.message}")
    except Exception as e:
        logger.error(f"状态更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="状态更新失败，请稍后重试")

# 服务器分组
@router.post("/groups/", response_model=ServerGroupResponse)
async def create_server_group(
    group_data: ServerGroupCreate,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """创建服务器分组"""
    try:
        server_service = ServerService(db)
        return server_service.create_server_group(group_data)
    except ValidationError as e:
        logger.warning(f"服务器分组创建验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"服务器分组创建失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器分组创建失败，请稍后重试")

@router.get("/groups/", response_model=List[ServerGroupResponse])
async def get_server_groups(
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取服务器分组列表"""
    server_service = ServerService(db)
    return server_service.get_server_groups()

@router.get("/groups/{group_id}", response_model=ServerGroupResponse)
async def get_server_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取指定服务器分组"""
    server_service = ServerService(db)
    group = server_service.get_server_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="服务器分组不存在")
    return group

@router.put("/groups/{group_id}", response_model=ServerGroupResponse)
async def update_server_group(
    group_id: int,
    group_data: ServerGroupCreate,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """更新服务器分组"""
    try:
        server_service = ServerService(db)
        group = server_service.update_server_group(group_id, group_data)
        if not group:
            raise HTTPException(status_code=404, detail="服务器分组不存在")
        return group
    except ValidationError as e:
        logger.warning(f"服务器分组更新验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"服务器分组更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器分组更新失败，请稍后重试")

@router.delete("/groups/{group_id}")
async def delete_server_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """删除服务器分组"""
    server_service = ServerService(db)
    success = server_service.delete_server_group(group_id)
    if not success:
        raise HTTPException(status_code=404, detail="服务器分组不存在")
    return {"message": "服务器分组删除成功"}

# 批量操作接口
@router.post("/batch/power", response_model=BatchPowerResponse)
async def batch_power_control(
    request: BatchPowerRequest,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """批量电源控制"""
    try:
        server_service = ServerService(db)
        results = await server_service.batch_power_control(
            server_ids=request.server_ids,
            action=request.action
        )
        
        # 统计结果
        total_count = len(results)
        success_count = sum(1 for r in results if r.success)
        failed_count = total_count - success_count
        
        logger.info(f"批量电源操作完成: 总数{total_count}, 成功{success_count}, 失败{failed_count}")
        
        return BatchPowerResponse(
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            results=results
        )
        
    except ValidationError as e:
        logger.warning(f"批量电源操作验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"批量电源操作失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量操作失败，请稍后重试")


class BatchUpdateMonitoringRequest(BaseModel):
    """批量更新监控状态请求"""
    server_ids: List[int] = Field(..., min_length=1, max_length=100, description="服务器ID列表")
    monitoring_enabled: bool = Field(..., description="监控启用状态")

@router.post("/batch/monitoring", response_model=BatchPowerResponse)
async def batch_update_monitoring(
    request: BatchUpdateMonitoringRequest,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """批量更新服务器监控状态"""
    try:
        server_service = ServerService(db)
        results = await server_service.batch_update_monitoring(
            server_ids=request.server_ids,
            monitoring_enabled=request.monitoring_enabled
        )
        
        # 统计结果
        total_count = len(results)
        success_count = sum(1 for r in results if r.success)
        failed_count = total_count - success_count
        
        logger.info(f"批量更新监控状态完成: 总数{total_count}, 成功{success_count}, 失败{failed_count}")
        
        return BatchPowerResponse(
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            results=results
        )
        
    except ValidationError as e:
        logger.warning(f"批量更新监控状态验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"批量更新监控状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量更新监控状态失败，请稍后重试")

# Redfish支持检查响应模型
class RedfishSupportResponse(BaseModel):
    """Redfish支持检查响应"""
    supported: bool = Field(..., description="是否支持Redfish")
    version: Optional[str] = Field(None, description="Redfish版本")
    error: Optional[str] = Field(None, description="错误信息")
    service_root: Optional[dict] = Field(None, description="Redfish服务根信息")

# LED状态响应模型
class LEDStatusResponse(BaseModel):
    """LED状态响应"""
    supported: bool = Field(..., description="是否支持LED控制")
    led_state: str = Field(..., description="LED状态（On, Off, Unknown）")
    error: Optional[str] = Field(None, description="错误信息")

# LED控制响应模型
class LEDControlResponse(BaseModel):
    """LED控制响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果信息")
    error: Optional[str] = Field(None, description="错误信息")

@router.post("/{server_id}/redfish-check", response_model=RedfishSupportResponse)
async def check_redfish_support(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """检查服务器BMC是否支持Redfish"""
    try:
        server_service = ServerService(db)
        result = await server_service.check_redfish_support(server_id)
        return result
    except ValidationError as e:
        logger.warning(f"Redfish检查验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except IPMIError as e:
        logger.error(f"Redfish检查失败: {e.message}")
        raise HTTPException(status_code=500, detail=f"检查失败: {e.message}")
    except Exception as e:
        logger.error(f"Redfish检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail="检查失败，请稍后重试")

@router.get("/{server_id}/led-status", response_model=LEDStatusResponse)
async def get_led_status(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """获取服务器LED状态"""
    try:
        server_service = ServerService(db)
        result = await server_service.get_server_led_status(server_id)
        return result
    except ValidationError as e:
        logger.warning(f"LED状态查询验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except IPMIError as e:
        logger.error(f"LED状态查询失败: {e.message}")
        raise HTTPException(status_code=500, detail=f"查询失败: {e.message}")
    except Exception as e:
        logger.error(f"LED状态查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")

@router.post("/{server_id}/led-on", response_model=LEDControlResponse)
async def turn_on_led(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """点亮服务器LED"""
    try:
        server_service = ServerService(db)
        result = await server_service.set_server_led_state(server_id, "On")
        return result
    except ValidationError as e:
        logger.warning(f"LED点亮验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except IPMIError as e:
        logger.error(f"LED点亮失败: {e.message}")
        raise HTTPException(status_code=500, detail=f"操作失败: {e.message}")
    except Exception as e:
        logger.error(f"LED点亮失败: {str(e)}")
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")

@router.post("/{server_id}/led-off", response_model=LEDControlResponse)
async def turn_off_led(
    server_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(AuthService.get_current_user)
):
    """关闭服务器LED"""
    try:
        server_service = ServerService(db)
        result = await server_service.set_server_led_state(server_id, "Off")
        return result
    except ValidationError as e:
        logger.warning(f"LED关闭验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except IPMIError as e:
        logger.error(f"LED关闭失败: {e.message}")
        raise HTTPException(status_code=500, detail=f"操作失败: {e.message}")
    except Exception as e:
        logger.error(f"LED关闭失败: {str(e)}")
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")
