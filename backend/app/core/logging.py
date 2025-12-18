import logging
import logging.config
import os
from pathlib import Path

from app.core.config import settings

def setup_logging():
    """设置应用日志配置"""
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 根据DEBUG环境变量确定日志级别
    # 如果环境变量DEBUG=true，则将根日志级别和控制台级别都设为DEBUG
    debug_mode = os.getenv("DEBUG", "").lower() == "true"
    log_level = "DEBUG" if debug_mode else settings.LOG_LEVEL
    console_level = "DEBUG" if debug_mode else "INFO"
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": console_level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": settings.LOG_FILE,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file"],
        },
        "loggers": {
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "INFO",
                "handlers": ["file"],
                "propagate": False,
            },
            "aiosqlite": {
                "level": "INFO",
                "handlers": ["file"],
                "propagate": False,
            },
        },
    }
    
    logging.config.dictConfig(logging_config)