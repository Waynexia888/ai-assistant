import json
from app.domain.models.event import Event
from app.infrastructure.db.postgres import get_pool


def _json_loads(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


class PostgresEventRepository:
    async def append_event(self, task_id: str, event: Event) -> int:
        pool = await get_pool()
        event_json = event.model_dump(mode="json")
        event_status = event_json.get("status")

        async with pool.acquire() as conn:
            async with conn.transaction():
                existing = await conn.fetchrow(
                    "SELECT event_seq FROM agent.events WHERE id = $1",
                    event.id,
                )
                if existing is not None:
                    return int(existing["event_seq"])

                # Lock the task row so event_seq is unique and ordered per task.
                await conn.execute(
                    "SELECT 1 FROM agent.tasks WHERE id = $1 FOR UPDATE",
                    task_id,
                )

                next_event_seq = await conn.fetchval(
                    """
                    SELECT COALESCE(MAX(event_seq), 0) + 1
                    FROM agent.events
                    WHERE task_id = $1
                    """,
                    task_id,
                )

                row = await conn.fetchrow(
                    """
                    INSERT INTO agent.events (
                        id, task_id, event_seq, event_type, event_status, event_json, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
                    RETURNING event_seq
                    """,
                    event.id,
                    task_id,
                    next_event_seq,
                    event_json.get("type"),
                    event_status,
                    json.dumps(event_json, ensure_ascii=False),
                    event.created_at,
                )

        return int(row["event_seq"])
    

    async def list_events(
        self,
        task_id: str,
        after: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        pool = await get_pool()
        safe_limit = max(1, min(limit, 500))

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_seq, event_type, event_status, event_json, created_at
                FROM agent.events
                WHERE task_id = $1 AND event_seq > $2
                ORDER BY event_seq ASC
                LIMIT $3
                """,
                task_id,
                after,
                safe_limit,
            )

        return [
            {
                "event_seq": int(row["event_seq"]),
                "event_type": row["event_type"],
                "event_status": row["event_status"],
                "created_at": row["created_at"].isoformat(),
                "event": _json_loads(row["event_json"]),
            }
            for row in rows
        ]