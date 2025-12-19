from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, servers, monitoring, discovery, audit_logs, backup, config

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(servers.router, prefix="/servers", tags=["servers"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit_logs"])
api_router.include_router(backup.router, prefix="/backup", tags=["backup"])
api_router.include_router(config.router, prefix="/config", tags=["config"])