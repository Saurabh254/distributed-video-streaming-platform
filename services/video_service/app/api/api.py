from fastapi import APIRouter

from app.api.routes.events import router as events_router
from app.api.routes.live import router as live_router
from app.api.routes.upload import router as upload_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(upload_router)
api_router.include_router(events_router)
api_router.include_router(live_router)
