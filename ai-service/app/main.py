from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health_routes import router as health_router
from app.api.internal_chat_routes import router as internal_chat_router
from app.api.rag_routes import router as rag_router
from app.api.task_routes import router as task_router
from app.api.task_routes import task_service
from app.core.config import settings
from app.infrastructure.mcp.config import create_playwright_mcp_config
from app.infrastructure.mcp.runtime import MCPRuntime


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = create_playwright_mcp_config(
        enabled=settings.MCP_PLAYWRIGHT_ENABLED,
        command=settings.MCP_PLAYWRIGHT_COMMAND,
        args=settings.MCP_PLAYWRIGHT_ARGS,
    )
    runtime = MCPRuntime(config)
    app.state.playwright_mcp = runtime
    await runtime.start(task_service.tool_registry)
    try:
        yield
    finally:
        await runtime.close()

app = FastAPI(
    title="AI Assistant API",
    version="0.1.0",
    lifespan=lifespan,
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
app.include_router(internal_chat_router)
app.include_router(rag_router, prefix="/api")
app.include_router(task_router)
