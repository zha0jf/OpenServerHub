from typing import List
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 项目信息
    PROJECT_NAME: str = "OpenServerHub"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置 (开发阶段使用SQLite)
    DATABASE_URL: str = "sqlite:///./openshub.db"
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8天
    ALGORITHM: str = "HS256"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React前端
        "http://127.0.0.1:3000",
    ]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # IPMI配置
    IPMI_CONNECTION_POOL_SIZE: int = 50
    IPMI_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()