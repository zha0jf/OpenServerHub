from typing import List, Optional, Union
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 项目信息
    PROJECT_NAME: str = "OpenServerHub"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置 (开发阶段使用SQLite)
    # 统一使用与Docker Compose一致的路径
    DATABASE_URL: str = "sqlite:///./data/openserverhub.db"
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8天
    ALGORITHM: str = "HS256"
    
    # CORS配置 - 支持字符串和列表两种格式
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",  # React前端
        "http://127.0.0.1:3000",
    ]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # IPMI配置
    IPMI_CONNECTION_POOL_SIZE: int = 50
    IPMI_TIMEOUT: int = 30
    
    # 定时任务配置
    POWER_STATE_REFRESH_INTERVAL: int = 3  # 电源状态刷新间隔（分钟）
    POWER_STATE_REFRESH_ENABLED: bool = True  # 是否启用自动刷新
    
    # 监控系统配置
    MONITORING_ENABLED: bool = True  # 默认启用监控
    MONITORING_INTERVAL: int = 5  # 监控数据采集间隔（分钟）
    PROMETHEUS_URL: str = "http://prometheus:9090"
    GRAFANA_URL: str = "http://grafana:3000"
    GRAFANA_API_KEY: str = os.getenv("GRAFANA_API_KEY", "your-grafana-api-key-here")
    PROMETHEUS_TARGETS_PATH: str = "/etc/prometheus/targets/ipmi-targets.json"
    
    class Config:
        env_file = ".env"

settings = Settings()