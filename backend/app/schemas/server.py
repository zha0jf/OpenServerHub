from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.server import ServerStatus, PowerState

class ServerBase(BaseModel):
    name: str
    hostname: str
    ipmi_ip: str
    ipmi_username: str
    ipmi_port: int = 623
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    group_id: Optional[int] = None

class ServerCreate(ServerBase):
    ipmi_password: str

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ipmi_ip: Optional[str] = None
    ipmi_username: Optional[str] = None
    ipmi_password: Optional[str] = None
    ipmi_port: Optional[int] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    group_id: Optional[int] = None

class ServerResponse(ServerBase):
    id: int
    status: ServerStatus
    power_state: PowerState
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ServerGroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class ServerGroupCreate(ServerGroupBase):
    pass

class ServerGroupResponse(ServerGroupBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True