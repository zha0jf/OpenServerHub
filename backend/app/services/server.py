from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.server import Server, ServerGroup, ServerStatus, PowerState
from app.schemas.server import ServerCreate, ServerUpdate, ServerGroupCreate
from app.services.ipmi import IPMIService
from app.core.exceptions import ValidationError, IPMIError
import logging

logger = logging.getLogger(__name__)

class ServerService:
    def __init__(self, db: Session):
        self.db = db
        self.ipmi_service = IPMIService()

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
        
        # 检查名称唯一性
        if "name" in update_data and update_data["name"] != db_server.name:
            if self.get_server_by_name(update_data["name"]):
                raise ValidationError("服务器名称已存在")
        
        # 检查IPMI IP唯一性
        if "ipmi_ip" in update_data and update_data["ipmi_ip"] != db_server.ipmi_ip:
            if self.get_server_by_ipmi_ip(update_data["ipmi_ip"]):
                raise ValidationError("IPMI IP地址已存在")
        
        # 记录IPMI相关信息是否发生变化
        ipmi_changed = any(key in update_data for key in ['ipmi_ip', 'ipmi_username', 'ipmi_password', 'ipmi_port'])
        
        # 更新服务器信息
        for field, value in update_data.items():
            setattr(db_server, field, value)
        
        self.db.commit()
        self.db.refresh(db_server)
        
        # 如果IPMI相关信息发生变化，记录日志建议刷新状态
        if ipmi_changed:
            logger.info(f"服务器 {db_server.id} IPMI信息已更新，建议立即刷新状态")
        
        return db_server

    def delete_server(self, server_id: int) -> bool:
        """删除服务器"""
        db_server = self.get_server(server_id)
        if not db_server:
            return False
        
        self.db.delete(db_server)
        self.db.commit()
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