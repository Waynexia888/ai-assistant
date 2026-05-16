from fastapi import FastAPI
from app.api.health_routes import router as health_router

app = FastAPI(
    title="AI Assistant API",
    version="0.1.0",
)

app.include_router(health_router, prefix="/api")