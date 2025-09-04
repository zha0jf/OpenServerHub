from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MonitoringRecordResponse(BaseModel):
    id: int
    server_id: int
    metric_type: str
    metric_name: str
    value: float
    unit: Optional[str] = None
    status: Optional[str] = None
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    timestamp: datetime

    class Config:
        from_attributes = True