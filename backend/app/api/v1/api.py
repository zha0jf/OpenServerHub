from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, servers, monitoring

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(servers.router, prefix="/servers", tags=["servers"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])