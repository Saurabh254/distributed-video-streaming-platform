from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router

auth_app = APIRouter(prefix="/api/v1")
auth_app.include_router(health_router)
auth_app.include_router(auth_router)
