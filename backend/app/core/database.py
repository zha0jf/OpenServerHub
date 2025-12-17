from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 同步引擎配置 (Sync Engine) - 主要用于 Alembic 迁移或开发调试
# -----------------------------------------------------------------------------

# 判断是否是 SQLite
is_sqlite = "sqlite" in settings.DATABASE_URL

# 同步引擎配置
sync_engine_kwargs = {
    "echo": True if settings.ENVIRONMENT == "development" else False
}

if is_sqlite:
    sync_engine_kwargs["connect_args"] = {"check_same_thread": False}
    # 增加等待锁的超时时间 (秒)，防止 database is locked
    sync_engine_kwargs["connect_args"]["timeout"] = 30

engine = create_engine(
    settings.DATABASE_URL,
    **sync_engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -----------------------------------------------------------------------------
# 异步引擎配置 (Async Engine) - 核心业务使用
# -----------------------------------------------------------------------------

# 构造连接参数
connect_args = {}
engine_kwargs = {
    "echo": True if settings.ENVIRONMENT == "development" else False,
    "pool_pre_ping": True,
}

if is_sqlite:
    # 修正连接字符串以使用 aiosqlite 驱动
    async_database_url = settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    # 允许在不同线程/协程中使用连接
    connect_args["check_same_thread"] = False
    # 增加等待锁的超时时间 (秒)，防止 database is locked
    connect_args["timeout"] = 30  
    
    # SQLite 通常不需要 pool_recycle，且默认使用 NullPool 或 StaticPool
else:
    # 生产环境 (MySQL/PostgreSQL) 配置
    async_database_url = settings.DATABASE_URL
    # [关键配置] 设置连接池大小，配合 IPMI Service 的 Semaphore
    # 如果 Semaphore=10，这里建议 pool_size >= 20
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_recycle"] = settings.DATABASE_POOL_RECYCLE
    engine_kwargs["pool_pre_ping"] = settings.DATABASE_POOL_PRE_PING
    engine_kwargs["echo"] = settings.DATABASE_ECHO

# 创建异步引擎
async_engine = create_async_engine(
    async_database_url,
    connect_args=connect_args,
    **engine_kwargs
)

# -----------------------------------------------------------------------------
# Session 工厂
# -----------------------------------------------------------------------------

# [关键优化] 统一导出 AsyncSessionLocal
# 服务层代码应该导入这个工厂，而不是自己重新定义
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # 避免提交后属性访问触发额外的 IO
)

Base = declarative_base()

# -----------------------------------------------------------------------------
# 依赖注入 (Dependencies)
# -----------------------------------------------------------------------------

def get_db():
    """同步数据库依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """异步数据库依赖 - 用于 FastAPI 路由"""
    async with AsyncSessionLocal() as session:
        yield session

# -----------------------------------------------------------------------------
# 健康检查
# -----------------------------------------------------------------------------

async def periodic_health_check():
    """定期执行数据库健康检查，保持连接活跃"""
    while True:
        try:
            async with AsyncSessionLocal() as session:
                # 执行一个简单的查询来保持连接活跃
                await session.execute(text("SELECT 1"))
                # logger.debug("数据库健康检查成功") # 避免日志刷屏，建议注释掉
        except Exception as e:
            logger.warning(f"数据库健康检查失败: {e}")
        
        # 每30分钟执行一次健康检查
        await asyncio.sleep(1800)