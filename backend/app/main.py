from fastapi import FastAPI
from app.api.health_routes import router as health_router
from app.api.chat_routes import router as chat_router

app = FastAPI(
    title="AI Assistant API",
    version="0.1.0",
)

app.include_router(health_router, prefix="/api")
app.include_router(chat_router, prefix="/api")