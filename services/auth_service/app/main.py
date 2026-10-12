import uvicorn
from fastapi import FastAPI

from app.api.api import auth_app
from app.api.routes.health import router as health_router
from app.core.lifespan import lifespan

app = FastAPI(
    title="fineshare",
    version="0.0.1",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_app)

if __name__ == "__main__":
    uvicorn.run(app)
