import os
import shlex
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE: str | None = os.getenv("OPENAI_API_BASE")

    DEEPSEEK_API_KEY: str | None = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_API_BASE: str | None = os.getenv("DEEPSEEK_API_BASE")

    BASE_MODEL: str = os.getenv("BASE_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    QDRANT_URL: str | None = os.getenv("QDRANT_URL")
    QDRANT_API_KEY: str | None = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "ai_assistant_rag")

    USER_AGENT: str = os.getenv("USER_AGENT") or "ai-assistant/0.1"

    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "../data/vector_db")
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    AGENT_MODE: str = os.getenv("AGENT_MODE", "langchain")

    MCP_PLAYWRIGHT_ENABLED: bool = (
        os.getenv("MCP_PLAYWRIGHT_ENABLED", "false").lower() == "true"
    )
    MCP_PLAYWRIGHT_COMMAND: str = os.getenv("MCP_PLAYWRIGHT_COMMAND", "npx")
    MCP_PLAYWRIGHT_ARGS: list[str] = shlex.split(
        os.getenv(
            "MCP_PLAYWRIGHT_ARGS",
            "-y @playwright/mcp@latest --headless",
        )
    )


settings = Settings()

if settings.USER_AGENT:
    os.environ["USER_AGENT"] = settings.USER_AGENT
