import asyncpg

from app.core.config import settings

_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if settings.DATABASE_URL is None:
            raise RuntimeError("DATABASE_URL is not configured.")
        _pool = await asyncpg.create_pool(settings.DATABASE_URL)
    
    return _pool

async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


