from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health_routes import router as health_router
from app.api.chat_routes import router as chat_router

app = FastAPI(
    title="AI Assistant API",
    version="0.1.0",
)

# CORS 配置：允许前端 localhost:5173 访问后端 localhost:8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(chat_router, prefix="/api")