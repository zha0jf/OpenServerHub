from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
from concurrent.futures import as_completed
from collections import defaultdict

from app.models.server import Server, ServerGroup, ServerStatus, PowerState
from app.schemas.server import ServerCreate, ServerUpdate, ServerGroupCreate, BatchOperationResult
from app.services.ipmi import IPMIService
from app.services.monitoring import MonitoringService
from app.services.server_monitoring import ServerMonitoringService
from app.core.exceptions import ValidationError, IPMIError
import logging

logger = logging.getLogger(__name__)

class ServerService:
    def __init__(self, db: Session):
        self.db = db
        self.ipmi_service = IPMIService()
        self.monitoring_service = ServerMonitoringService(db)

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
        
        # 异步处理监控配置
        # 注意：在实际应用中，这里可能需要使用后台任务处理
        # asyncio.create_task(self.monitoring_service.on_server_added(db_server))
        
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
        original_ipmi_ip = db_server.ipmi_ip
        original_ipmi_username = db_server.ipmi_username
        original_ipmi_password = db_server.ipmi_password
        original_ipmi_port = db_server.ipmi_port
        
        # 更新服务器信息
        for field, value in update_data.items():
            setattr(db_server, field, value)
        
        self.db.commit()
        self.db.refresh(db_server)
        
        # 检查IPMI相关信息是否发生变化
        ipmi_changed = (
            original_ipmi_ip != db_server.ipmi_ip or
            original_ipmi_username != db_server.ipmi_username or
            original_ipmi_password != db_server.ipmi_password or
            original_ipmi_port != db_server.ipmi_port
        )
        
        # 如果IPMI相关信息发生变化，记录日志建议刷新状态
        if ipmi_changed:
            logger.info(f"服务器 {db_server.id} IPMI信息已更新，建议立即刷新状态")
        
        # 异步处理监控配置更新
        # asyncio.create_task(self.monitoring_service.on_server_updated(db_server))
        
        return db_server

    def delete_server(self, server_id: int) -> bool:
        """删除服务器"""
        db_server = self.get_server(server_id)
        if not db_server:
            return False
        
        self.db.delete(db_server)
        self.db.commit()
        
        # 异步处理监控配置清理
        # asyncio.create_task(self.monitoring_service.on_server_deleted(server_id))
        
        return True

    async def power_control(self, server_id: int, action: str) -> Dict[str, Any]:
        """服务器电源控制"""
        db_server = self.get_server(server_id)
        if not db_server:
            raise ValidationError("服务器不存在")
        
        try:
            result = await self.ipmi_service.power_control(
                ip=db_server.ipmi_ip,
                username=db_server.ipmi_username,
                password=db_server.ipmi_password,
                action=action,
                port=db_server.ipmi_port
            )
            
            # 更新服务器最后操作时间
            db_server.last_seen = datetime.now()
            self.db.commit()
            
            return result
            
        except IPMIError as e:
            # 更新服务器状态为错误
            db_server.status = ServerStatus.ERROR
            self.db.commit()
            raise e

    async def update_server_status(self, server_id: int) -> Dict[str, Any]:
        """更新服务器状态"""
        db_server = self.get_server(server_id)
        if not db_server:
            raise ValidationError("服务器不存在")
        
        try:
            # 获取电源状态
            power_state = await self.ipmi_service.get_power_state(
                ip=db_server.ipmi_ip,
                username=db_server.ipmi_username,
                password=db_server.ipmi_password,
                port=db_server.ipmi_port
            )
            
            # 获取系统信息
            system_info = await self.ipmi_service.get_system_info(
                ip=db_server.ipmi_ip,
                username=db_server.ipmi_username,
                password=db_server.ipmi_password,
                port=db_server.ipmi_port
            )
            
            # 更新服务器状态
            db_server.status = ServerStatus.ONLINE
            db_server.power_state = PowerState.ON if power_state == 'on' else PowerState.OFF
            db_server.last_seen = datetime.now()
            
            # 更新系统信息
            if system_info.get('manufacturer'):
                db_server.manufacturer = system_info['manufacturer']
            if system_info.get('product'):
                db_server.model = system_info['product']
            
            self.db.commit()
            
            return {
                "status": "success",
                "power_state": power_state,
                "system_info": system_info
            }
            
        except IPMIError as e:
            # 更新服务器状态为离线或错误
            db_server.status = ServerStatus.OFFLINE
            db_server.power_state = PowerState.UNKNOWN
            self.db.commit()
            
            return {
                "status": "error",
                "message": str(e)
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
        db_group.name = group_data.name
        db_group.description = group_data.description
        
        self.db.commit()
        self.db.refresh(db_group)
        return db_group

    # 批量操作功能
    async def batch_power_control(self, server_ids: List[int], action: str) -> List[BatchOperationResult]:
        """批量电源控制"""
        results = []
        
        # 获取所有有效的服务器
        servers = self.db.query(Server).filter(Server.id.in_(server_ids)).all()
        
        # 检查是否有不存在的服务器ID
        found_ids = {server.id for server in servers}
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
                        server_id=server.id,
                        server_name=server.name,
                        success=False,
                        message="失败",
                        error=str(task_results[i])
                    ))
                else:
                    results.append(task_results[i])
        
        return results
    
    async def _single_power_control(self, server: Server, action: str) -> BatchOperationResult:
        """单个服务器电源控制"""
        try:
            await self.ipmi_service.power_control(
                ip=server.ipmi_ip,
                username=server.ipmi_username,
                password=server.ipmi_password,
                action=action,
                port=server.ipmi_port
            )
            
            # 更新服务器最后操作时间
            server.last_seen = datetime.now()
            self.db.commit()
            
            return BatchOperationResult(
                server_id=server.id,
                server_name=server.name,
                success=True,
                message=f"电源{action}操作成功"
            )
            
        except IPMIError as e:
            # 更新服务器状态为错误
            server.status = ServerStatus.ERROR
            self.db.commit()
            
            return BatchOperationResult(
                server_id=server.id,
                server_name=server.name,
                success=False,
                message="失败",
                error=f"IPMI操作失败: {str(e)}"
            )
        except Exception as e:
            logger.error(f"服务器 {server.id} 电源控制异常: {str(e)}")
            return BatchOperationResult(
                server_id=server.id,
                server_name=server.name,
                success=False,
                message="失败",
                error=f"内部错误: {str(e)}"
            )
    
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
            if server.group_id:
                group = self.get_server_group(server.group_id)
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
            manufacturer = server.manufacturer or "未知"
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