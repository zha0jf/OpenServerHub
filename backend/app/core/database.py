from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

# SQLite配置（开发阶段）
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite需要
    echo=True if settings.ENVIRONMENT == "development" else False  # 仅在开发环境显示SQL
)

# 异步引擎配置 - 添加连接池配置
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False},
    echo=True if settings.ENVIRONMENT == "development" else False,
    # 添加连接池配置
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 超出pool_size后最多可创建的连接数
    pool_recycle=3600,  # 连接回收时间（秒），1小时
    pool_pre_ping=True,  # 在使用连接前先ping一下，确保连接有效
    pool_timeout=30,  # 获取连接的超时时间
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 异步数据库依赖 - 使用正确的实现方式
async def get_async_db():
    async with AsyncSession(bind=async_engine) as session:
        yield session

# 定期健康检查函数
async def periodic_health_check():
    """定期执行数据库健康检查，保持连接活跃"""
    while True:
        try:
            async with AsyncSession(bind=async_engine) as session:
                # 执行一个简单的查询来保持连接活跃
                result = await session.execute(text("SELECT 1"))
                logger.debug("数据库健康检查成功")
        except Exception as e:
            logger.warning(f"数据库健康检查失败: {e}")
        
        # 每30分钟执行一次健康检查
        await asyncio.sleep(1800)