from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
from concurrent.futures import as_completed
from collections import defaultdict
from sqlalchemy import update, select

from app.models.server import Server, ServerGroup, ServerStatus, PowerState
from app.schemas.server import ServerCreate, ServerUpdate, ServerGroupCreate, BatchOperationResult
from app.services.ipmi import IPMIService
from app.services.monitoring import MonitoringService
from app.services.server_monitoring import PrometheusConfigManager
from app.services.server_monitoring_service import ServerMonitoringService
from app.core.exceptions import ValidationError, IPMIError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ServerService:
    def __init__(self, db: Session):
        self.db = db
        self.ipmi_service = IPMIService()
        # 注意：这里传入的是同步会话，仅用于同步方法
        # 异步方法需要创建新的异步监控服务实例
        self.monitoring_service = MonitoringService(db) if hasattr(db, 'query') else None
        self.server_monitoring_service = ServerMonitoringService(db)

    def create_server(self, server_data: ServerCreate) -> Server:
        """创建服务器"""
        # 检查IPMI IP是否已存在
        if self.get_server_by_ipmi_ip(server_data.ipmi_ip):
            raise ValidationError("IPMI IP地址已存在")
        
        # 检查服务器名是否已存在
        if self.get_server_by_name(server_data.name):
            raise ValidationError("服务器名称已存在")
        
        # 创建服务器
        db_server = Server(
            name=server_data.name,
            ipmi_ip=server_data.ipmi_ip,
            ipmi_username=server_data.ipmi_username,
            ipmi_password=server_data.ipmi_password,
            ipmi_port=server_data.ipmi_port,
            monitoring_enabled=server_data.monitoring_enabled,
            manufacturer=server_data.manufacturer,
            model=server_data.model,
            serial_number=server_data.serial_number,
            description=server_data.description,
            tags=server_data.tags,
            group_id=server_data.group_id
        )
        
        self.db.add(db_server)
        self.db.commit()
        self.db.refresh(db_server)
        
        # 异步处理监控配置（仅在启用监控时）
        if settings.MONITORING_ENABLED and bool(db_server.monitoring_enabled):
            asyncio.create_task(self.server_monitoring_service.on_server_added(db_server))
        
        # 标记需要状态刷新（前端会调用状态刷新接口）
        logger.info(f"服务器 {db_server.id} 创建成功，建议立即刷新状态")
        
        return db_server

    def get_server(self, server_id: int) -> Optional[Server]:
        """根据ID获取服务器"""
        return self.db.query(Server).filter(Server.id == server_id).first()

    def get_server_by_name(self, name: str) -> Optional[Server]:
        """根据名称获取服务器"""
        return self.db.query(Server).filter(Server.name == name).first()

    def get_server_by_ipmi_ip(self, ipmi_ip: str) -> Optional[Server]:
        """根据IPMI IP获取服务器"""
        return self.db.query(Server).filter(Server.ipmi_ip == ipmi_ip).first()

    def get_servers(self, skip: int = 0, limit: int = 100, group_id: Optional[int] = None) -> List[Server]:
        """获取服务器列表"""
        query = self.db.query(Server)
        
        if group_id is not None:
            query = query.filter(Server.group_id == group_id)
        
        return query.offset(skip).limit(limit).all()

    def update_server(self, server_id: int, server_data: ServerUpdate) -> Optional[Server]:
        """更新服务器信息"""
        db_server = self.get_server(server_id)
        if not db_server:
            return None
        
        # 记录原始监控启用状态
        original_monitoring_enabled = bool(db_server.monitoring_enabled)
        
        update_data = server_data.model_dump(exclude_unset=True)
        
        # 如果密码字段存在但为空，则从更新数据中移除
        if "ipmi_password" in update_data and not update_data["ipmi_password"]:
            del update_data["ipmi_password"]
        
        # 检查名称唯一性
        if "name" in update_data and update_data["name"] != db_server.name:
            if self.get_server_by_name(update_data["name"]):
                raise ValidationError("服务器名称已存在")
        
        # 检查IPMI IP唯一性
        if "ipmi_ip" in update_data and update_data["ipmi_ip"] != db_server.ipmi_ip:
            if self.get_server_by_ipmi_ip(update_data["ipmi_ip"]):
                raise ValidationError("IPMI IP地址已存在")
        
        # 记录原始值用于比较
        original_ipmi_ip = str(db_server.ipmi_ip) if db_server.ipmi_ip is not None else ""
        original_ipmi_username = str(db_server.ipmi_username) if db_server.ipmi_username is not None else ""
        original_ipmi_password = str(db_server.ipmi_password) if db_server.ipmi_password is not None else ""
        original_ipmi_port = int(str(db_server.ipmi_port)) if db_server.ipmi_port is not None else 623
        
        # 更新服务器信息
        for field, value in update_data.items():
            setattr(db_server, field, value)
        
        self.db.commit()
        self.db.refresh(db_server)
        
        # 检查IPMI相关信息是否发生变化
        new_ipmi_ip = str(db_server.ipmi_ip) if db_server.ipmi_ip is not None else ""
        new_ipmi_username = str(db_server.ipmi_username) if db_server.ipmi_username is not None else ""
        new_ipmi_password = str(db_server.ipmi_password) if db_server.ipmi_password is not None else ""
        new_ipmi_port = int(str(db_server.ipmi_port)) if db_server.ipmi_port is not None else 623
        
        ipmi_changed = (
            original_ipmi_ip != new_ipmi_ip or
            original_ipmi_username != new_ipmi_username or
            original_ipmi_password != new_ipmi_password or
            original_ipmi_port != new_ipmi_port
        )
        
        # 如果IPMI相关信息发生变化，记录日志建议刷新状态
        if ipmi_changed:
            logger.info(f"服务器 {db_server.id} IPMI信息已更新，建议立即刷新状态")
        
        # 异步处理监控配置更新（仅在启用监控时）
        if settings.MONITORING_ENABLED and (original_monitoring_enabled != bool(db_server.monitoring_enabled) or ipmi_changed):
            asyncio.create_task(self.server_monitoring_service.on_server_updated(db_server, original_monitoring_enabled))
        
        return db_server

    def delete_server(self, server_id: int) -> bool:
        """删除服务器"""
        db_server = self.get_server(server_id)
        if not db_server:
            return False
        
        # 记录服务器的监控启用状态
        was_monitoring_enabled = bool(db_server.monitoring_enabled)
        
        self.db.delete(db_server)
        self.db.commit()
        
        # 异步处理监控配置清理（仅在启用监控时）
        if settings.MONITORING_ENABLED and was_monitoring_enabled:
            asyncio.create_task(self.server_monitoring_service.on_server_deleted(server_id))
        
        return True

    async def _sync_monitoring_config(self):
        """同步监控配置"""
        logger.info("开始同步监控配置")
        
        try:
            # 检查监控是否启用
            if not settings.MONITORING_ENABLED:
                logger.debug("监控功能未启用，跳过配置同步")
                return
                
            logger.debug(f"监控功能已启用，开始同步配置")
            
            # 获取所有服务器
            servers = self.get_servers()
            logger.debug(f"获取到服务器列表，数量: {len(servers)}")
            
            # 同步Prometheus配置
            prometheus_manager = PrometheusConfigManager()
            logger.debug("创建PrometheusConfigManager实例")
            
            result = await prometheus_manager.sync_ipmi_targets(servers)
            
            if result:
                logger.info("监控配置同步完成")
            else:
                logger.error("监控配置同步失败")
                
        except Exception as e:
            logger.error(f"同步监控配置失败: {e}")
            logger.exception(e)  # 记录完整的异常堆栈

    async def power_control(self, server_id: int, action: str) -> Dict[str, Any]:
        """服务器电源控制"""
        db_server = self.get_server(server_id)
        if not db_server:
            raise ValidationError("服务器不存在")
        
        try:
            result = await self.ipmi_service.power_control(
                ip=str(db_server.ipmi_ip) if db_server.ipmi_ip is not None else "",
                username=str(db_server.ipmi_username) if db_server.ipmi_username is not None else "",
                password=str(db_server.ipmi_password) if db_server.ipmi_password is not None else "",
                action=action,
                port=int(str(db_server.ipmi_port)) if db_server.ipmi_port is not None else 623
            )
            
            # 更新服务器最后操作时间
            stmt = update(Server).where(Server.id == server_id).values(
                last_seen=datetime.utcnow()
            )
            self.db.execute(stmt)
            self.db.commit()
            
            return result
            
        except IPMIError as e:
            # 更新服务器状态为错误
            stmt = update(Server).where(Server.id == server_id).values(
                status=ServerStatus.ERROR
            )
            self.db.execute(stmt)
            self.db.commit()
            raise e

    async def update_server_status(self, server_id: int) -> Dict[str, Any]:
        """更新服务器状态"""
        db_server = self.get_server(server_id)
        if not db_server:
            raise ValidationError("服务器不存在")
        
        try:
            # 先进行IPMI检查
            # 获取电源状态
            power_state = await self.ipmi_service.get_power_state(
                ip=str(db_server.ipmi_ip) if db_server.ipmi_ip is not None else "",
                username=str(db_server.ipmi_username) if db_server.ipmi_username is not None else "",
                password=str(db_server.ipmi_password) if db_server.ipmi_password is not None else "",
                port=int(str(db_server.ipmi_port)) if db_server.ipmi_port is not None else 623
            )
            
            # 获取系统信息
            system_info = await self.ipmi_service.get_system_info(
                ip=str(db_server.ipmi_ip) if db_server.ipmi_ip is not None else "",
                username=str(db_server.ipmi_username) if db_server.ipmi_username is not None else "",
                password=str(db_server.ipmi_password) if db_server.ipmi_password is not None else "",
                port=int(str(db_server.ipmi_port)) if db_server.ipmi_port is not None else 623
            )
            
            # IPMI检查成功，继续检查Redfish支持情况
            redfish_info = await self.check_redfish_support(server_id)
            
            # 准备更新数据库的值
            power_state_enum = PowerState.ON if power_state == 'on' else PowerState.OFF
            update_values = {
                "status": ServerStatus.ONLINE,
                "power_state": power_state_enum,
                "last_seen": datetime.now()
            }
            
            # 只有在Redfish检查成功获得明确结果时，才更新Redfish相关字段
            if redfish_info.get("check_success", False):
                update_values["redfish_supported"] = redfish_info.get("supported")
                update_values["redfish_version"] = redfish_info.get("version") if redfish_info.get("supported") else None
            
            # 更新服务器状态
            stmt = update(Server).where(Server.id == server_id).values(**update_values)
            self.db.execute(stmt)
            self.db.commit()
            
            return {
                "status": "success",
                "power_state": power_state,
                "system_info": system_info,
                "redfish_info": redfish_info
            }
            
        except IPMIError as e:
            # IPMI检查失败，更新服务器状态为离线或错误，不检查Redfish
            stmt = update(Server).where(Server.id == server_id).values(
                status=ServerStatus.OFFLINE,
                power_state=PowerState.UNKNOWN
                # 不更新redfish相关字段
            )
            self.db.execute(stmt)
            self.db.commit()
            
            return {
                "status": "error",
                "message": str(e),
                "redfish_info": {
                    "supported": None,  # 未检查
                    "version": None,
                    "service_root": None,
                    "error": "IPMI检查失败，未进行Redfish检查",
                    "check_success": False
                }
            }

    # 服务器分组管理
    def create_server_group(self, group_data: ServerGroupCreate) -> ServerGroup:
        """创建服务器分组"""
        # 检查分组名是否已存在
        if self.get_server_group_by_name(group_data.name):
            raise ValidationError("分组名称已存在")
        
        db_group = ServerGroup(
            name=group_data.name,
            description=group_data.description
        )
        
        self.db.add(db_group)
        self.db.commit()
        self.db.refresh(db_group)
        return db_group

    def get_server_group(self, group_id: int) -> Optional[ServerGroup]:
        """根据ID获取服务器分组"""
        return self.db.query(ServerGroup).filter(ServerGroup.id == group_id).first()

    def get_server_group_by_name(self, name: str) -> Optional[ServerGroup]:
        """根据名称获取服务器分组"""
        return self.db.query(ServerGroup).filter(ServerGroup.name == name).first()

    def get_server_groups(self) -> List[ServerGroup]:
        """获取所有服务器分组"""
        return self.db.query(ServerGroup).all()

    def delete_server_group(self, group_id: int) -> bool:
        """删除服务器分组"""
        db_group = self.get_server_group(group_id)
        if not db_group:
            return False
        
        # 将分组下的服务器移除分组
        self.db.query(Server).filter(Server.group_id == group_id).update({"group_id": None})
        
        # 删除分组
        self.db.delete(db_group)
        self.db.commit()
        return True

    def update_server_group(self, group_id: int, group_data: ServerGroupCreate) -> Optional[ServerGroup]:
        """更新服务器分组"""
        db_group = self.get_server_group(group_id)
        if not db_group:
            return None
        
        # 检查名称唯一性（排除自己）
        if group_data.name != db_group.name:
            if self.get_server_group_by_name(group_data.name):
                raise ValidationError("分组名称已存在")
        
        # 更新分组信息
        stmt = update(ServerGroup).where(ServerGroup.id == group_id).values(
            name=group_data.name,
            description=group_data.description
        )
        self.db.execute(stmt)
        self.db.commit()
        
        # 刷新对象
        self.db.refresh(db_group)
        return db_group

    # 批量操作功能
    async def batch_power_control(self, server_ids: List[int], action: str) -> List[BatchOperationResult]:
        """批量电源控制"""
        results = []
        
        # 获取所有有效的服务器
        servers = self.db.query(Server).filter(Server.id.in_(server_ids)).all()
        
        # 检查是否有不存在的服务器ID
        found_ids = {int(str(server.id)) for server in servers}
        missing_ids = set(server_ids) - found_ids
        
        # 为不存在的服务器添加错误结果
        for missing_id in missing_ids:
            results.append(BatchOperationResult(
                server_id=missing_id,
                server_name=f"服务器{missing_id}",
                success=False,
                message="失败",
                error="服务器不存在"
            ))
        
        # 创建并发任务列表
        tasks = []
        for server in servers:
            task = self._single_power_control(server, action)
            tasks.append(task)
        
        # 并发执行所有任务，最大并发数为10
        semaphore = asyncio.Semaphore(10)
        
        async def limited_task(server, action):
            async with semaphore:
                return await self._single_power_control(server, action)
        
        # 执行所有任务
        task_results = await asyncio.gather(
            *[limited_task(server, action) for server in servers],
            return_exceptions=True
        )
        
        # 整理结果
        for i, server in enumerate(servers):
            if i < len(task_results):
                if isinstance(task_results[i], Exception):
                    results.append(BatchOperationResult(
                        server_id=int(str(server.id)),
                        server_name=str(server.name),
                        success=False,
                        message="失败",
                        error=str(task_results[i])
                    ))
                else:
                    results.append(task_results[i])
        
        return results
    
    async def batch_update_monitoring(self, server_ids: List[int], monitoring_enabled: bool) -> List[BatchOperationResult]:
        """批量更新服务器监控状态"""
        results = []
        
        # 获取所有有效的服务器
        servers = self.db.query(Server).filter(Server.id.in_(server_ids)).all()
        
        # 检查是否有不存在的服务器ID
        found_ids = {int(str(server.id)) for server in servers}
        missing_ids = set(server_ids) - found_ids
        
        # 为不存在的服务器添加错误结果
        for missing_id in missing_ids:
            results.append(BatchOperationResult(
                server_id=missing_id,
                server_name=f"服务器{missing_id}",
                success=False,
                message="失败",
                error="服务器不存在"
            ))
        
        # 更新每个服务器的监控状态
        for server in servers:
            try:
                # 记录原始监控启用状态
                original_monitoring_enabled = bool(server.monitoring_enabled)
                
                # 更新监控状态
                setattr(server, 'monitoring_enabled', monitoring_enabled)
                self.db.commit()
                self.db.refresh(server)
                
                # 异步处理监控配置更新（仅在启用监控时）
                if settings.MONITORING_ENABLED and original_monitoring_enabled != monitoring_enabled:
                    asyncio.create_task(self.server_monitoring_service.on_server_updated(server, original_monitoring_enabled))
                
                results.append(BatchOperationResult(
                    server_id=int(str(server.id)),
                    server_name=str(server.name),
                    success=True,
                    message=f"监控状态已{'启用' if monitoring_enabled else '禁用'}"
                ))
                
            except Exception as e:
                self.db.rollback()
                results.append(BatchOperationResult(
                    server_id=int(str(server.id)),
                    server_name=str(server.name),
                    success=False,
                    message="失败",
                    error=str(e)
                ))
        
        return results
    
    async def _single_power_control(self, server: Server, action: str) -> BatchOperationResult:
        """单个服务器电源控制"""
        try:
            await self.ipmi_service.power_control(
                ip=str(server.ipmi_ip) if server.ipmi_ip is not None else "",
                username=str(server.ipmi_username) if server.ipmi_username is not None else "",
                password=str(server.ipmi_password) if server.ipmi_password is not None else "",
                action=action,
                port=int(str(server.ipmi_port)) if server.ipmi_port is not None else 623
            )
            
            # 更新服务器最后操作时间
            stmt = update(Server).where(Server.id == server.id).values(
                last_seen=datetime.utcnow()
            )
            self.db.execute(stmt)
            self.db.commit()
            
            return BatchOperationResult(
                server_id=int(str(server.id)),
                server_name=str(server.name),
                success=True,
                message=f"电源{action}操作成功"
            )
            
        except IPMIError as e:
            # 更新服务器状态为错误
            stmt = update(Server).where(Server.id == server.id).values(
                status=ServerStatus.ERROR
            )
            self.db.execute(stmt)
            self.db.commit()
            
            return BatchOperationResult(
                server_id=int(str(server.id)),
                server_name=str(server.name),
                success=False,
                message="失败",
                error=f"IPMI操作失败: {str(e)}"
            )
        except Exception as e:
            logger.error(f"服务器 {server.id} 电源控制异常: {str(e)}")
            return BatchOperationResult(
                server_id=int(str(server.id)),
                server_name=str(server.name),
                success=False,
                message="失败",
                error=f"内部错误: {str(e)}"
            )
    
    async def check_redfish_support(self, server_id: int) -> Dict[str, Any]:
        """检查服务器BMC是否支持Redfish"""
        db_server = self.get_server(server_id)
        if not db_server:
            raise ValidationError("服务器不存在")
        
        try:
            # 调用IPMI服务检查Redfish支持
            result = await self.ipmi_service.check_redfish_support(
                bmc_ip=str(db_server.ipmi_ip) if db_server.ipmi_ip is not None else "",
                timeout=10
            )
            
            return result
            
        except IPMIError as e:
            logger.error(f"检查服务器 {server_id} Redfish支持失败: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"检查服务器 {server_id} Redfish支持时发生未知错误: {str(e)}")
            raise IPMIError(f"检查Redfish支持失败: {str(e)}")
    
    async def get_server_led_status(self, server_id: int) -> Dict[str, Any]:
        """
        获取服务器LED状态
        
        Args:
            server_id: 服务器ID
            
        Returns:
            Dict[str, Any]: 包含LED状态信息的字典
        """
        db_server = self.get_server(server_id)
        if not db_server:
            raise ValidationError("服务器不存在")
        
        # 检查服务器是否在线
        if db_server.status != ServerStatus.ONLINE:
            return {
                "supported": False,
                "led_state": "Unknown",
                "error": "服务器不在线，无法获取LED状态"
            }
        
        # 检查服务器是否支持Redfish
        if db_server.redfish_supported is not True:
            return {
                "supported": False,
                "led_state": "Unknown",
                "error": "服务器BMC不支持Redfish，无法获取LED状态"
            }
        
        try:
            # 调用IPMI服务获取LED状态
            result = await self.ipmi_service.get_redfish_led_status(
                bmc_ip=str(db_server.ipmi_ip) if db_server.ipmi_ip is not None else "",
                username=str(db_server.ipmi_username) if db_server.ipmi_username is not None else "",
                password=str(db_server.ipmi_password) if db_server.ipmi_password is not None else "",
                timeout=10
            )
            
            return result
            
        except Exception as e:
            logger.error(f"获取服务器 {server_id} LED状态失败: {str(e)}")
            return {
                "supported": False,
                "led_state": "Unknown",
                "error": f"获取LED状态失败: {str(e)}"
            }
    
    async def set_server_led_state(self, server_id: int, led_state: str) -> Dict[str, Any]:
        """
        设置服务器LED状态
        
        Args:
            server_id: 服务器ID
            led_state: LED状态（"On" 或 "Off"）
            
        Returns:
            Dict[str, Any]: 包含操作结果的字典
        """
        db_server = self.get_server(server_id)
        if not db_server:
            raise ValidationError("服务器不存在")
        
        # 检查服务器是否在线
        if db_server.status != ServerStatus.ONLINE:
            return {
                "success": False,
                "message": "操作失败",
                "error": "服务器不在线，无法设置LED状态"
            }
        
        # 检查服务器是否支持Redfish
        if db_server.redfish_supported is not True:
            return {
                "success": False,
                "message": "操作失败",
                "error": "服务器BMC不支持Redfish，无法设置LED状态"
            }
        
        try:
            # 调用IPMI服务设置LED状态
            result = await self.ipmi_service.set_redfish_led_state(
                bmc_ip=str(db_server.ipmi_ip) if db_server.ipmi_ip is not None else "",
                username=str(db_server.ipmi_username) if db_server.ipmi_username is not None else "",
                password=str(db_server.ipmi_password) if db_server.ipmi_password is not None else "",
                led_state=led_state,
                timeout=10
            )
            
            return result
            
        except Exception as e:
            logger.error(f"设置服务器 {server_id} LED状态失败: {str(e)}")
            return {
                "success": False,
                "message": "操作失败",
                "error": f"设置LED状态失败: {str(e)}"
            }

    def get_cluster_statistics(self, group_id: Optional[int] = None) -> Dict[str, Any]:
        """获取集群统计信息"""
        # 基本查询
        query = self.db.query(Server)
        if group_id is not None:
            query = query.filter(Server.group_id == group_id)
        
        servers = query.all()
        
        # 基础统计
        total_servers = len(servers)
        online_servers = sum(1 for s in servers if s.status == ServerStatus.ONLINE)
        offline_servers = sum(1 for s in servers if s.status == ServerStatus.OFFLINE)
        unknown_servers = sum(1 for s in servers if s.status == ServerStatus.UNKNOWN)
        
        # 电源状态统计
        power_on_servers = sum(1 for s in servers if s.power_state == PowerState.ON)
        power_off_servers = sum(1 for s in servers if s.power_state == PowerState.OFF)
        
        # 分组统计
        group_stats = defaultdict(lambda: {
            'total': 0,
            'online': 0, 
            'offline': 0,
            'unknown': 0,
            'power_on': 0,
            'power_off': 0
        })
        
        for server in servers:
            group_name = "未分组"
            if server.group_id is not None and int(str(server.group_id)) > 0:
                group = self.get_server_group(int(str(server.group_id)))
                if group:
                    group_name = group.name
            
            group_stats[group_name]['total'] += 1
            if server.status == ServerStatus.ONLINE:
                group_stats[group_name]['online'] += 1
            elif server.status == ServerStatus.OFFLINE:
                group_stats[group_name]['offline'] += 1
            else:
                group_stats[group_name]['unknown'] += 1
            
            if server.power_state == PowerState.ON:
                group_stats[group_name]['power_on'] += 1
            elif server.power_state == PowerState.OFF:
                group_stats[group_name]['power_off'] += 1
        
        # 厂商统计
        manufacturer_stats = defaultdict(int)
        for server in servers:
            manufacturer = str(server.manufacturer) if server.manufacturer is not None else "未知"
            manufacturer_stats[manufacturer] += 1
        
        return {
            'total_servers': total_servers,
            'online_servers': online_servers,
            'offline_servers': offline_servers,
            'unknown_servers': unknown_servers,
            'power_on_servers': power_on_servers,
            'power_off_servers': power_off_servers,
            'group_stats': dict(group_stats),
            'manufacturer_stats': dict(manufacturer_stats)
        }