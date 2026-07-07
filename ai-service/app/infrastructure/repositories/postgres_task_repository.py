import json
from typing import Any

from pydantic import TypeAdapter

from app.domain.models.event import Event
from app.domain.models.plan import ExecutionStatus, Plan, Step
from app.domain.models.step_result import StepResult
from app.domain.models.task import Task, TaskStatus
from app.infrastructure.db.postgres import get_pool

_event_adapter = TypeAdapter(Event)


def _json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value


def _step_result_to_db(result: StepResult | None) -> str | None:
    if result is None:
        return None

    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False)


def _step_result_from_db(value: Any) -> StepResult | None:
    if value is None:
        return None

    if isinstance(value, StepResult):
        return value

    try:
        data = _json_loads(value)
    except (TypeError, json.JSONDecodeError):
        return StepResult(type="text", content=str(value), data=str(value))

    if isinstance(data, dict):
        return StepResult.model_validate(data)

    return StepResult(type="text", content=str(data), data=data)


class PostgresTaskRepository:
    async def save(self, task: Task) -> Task:
        pool = await get_pool()

        async with pool.acquire() as conn:
            async with conn.transaction():
                await self._upsert_task(conn, task)

                if task.plan is not None:
                    await self._upsert_plan(conn, task.id, task.plan)
                    await self._sync_steps(conn, task.id, task.plan)

        return task

    async def get_task_by_id(self, task_id: str) -> Task | None:
        pool = await get_pool()

        async with pool.acquire() as conn:
            task_row = await conn.fetchrow(
                """
                SELECT id, message, status, summary, error, created_at, updated_at
                FROM agent.tasks
                WHERE id = $1
                """,
                task_id,
            )
            if task_row is None:
                return None

            plan_row = await conn.fetchrow(
                """
                SELECT id, title, goal, language, message, status, result, error
                FROM agent.plans
                WHERE task_id = $1
                """,
                task_id,
            )

            plan = None
            if plan_row is not None:
                step_rows = await conn.fetch(
                    """
                    SELECT id, description, tool_name, tool_arguments, status, result,
                           error, success, reason, attachments
                    FROM agent.steps
                    WHERE plan_id = $1
                    ORDER BY step_order ASC
                    """,
                    str(plan_row["id"]),
                )

                steps = [
                    Step(
                        id=str(row["id"]),
                        description=row["description"],
                        tool_name=row["tool_name"] or "echo",
                        tool_arguments=_json_loads(row["tool_arguments"]) or {},
                        status=ExecutionStatus(row["status"]),
                        result=_step_result_from_db(row["result"]),
                        error=row["error"],
                        success=bool(row["success"]),
                        reason=row["reason"],
                        attachments=_json_loads(row["attachments"]) or [],
                    )
                    for row in step_rows
                ]

                plan = Plan(
                    id=str(plan_row["id"]),
                    title=plan_row["title"] or "",
                    goal=plan_row["goal"] or "",
                    language=plan_row["language"] or "zh",
                    message=plan_row["message"] or "",
                    steps=steps,
                    status=ExecutionStatus(plan_row["status"]),
                    result=plan_row["result"],
                    error=plan_row["error"],
                )

            event_rows = await conn.fetch(
                """
                SELECT event_json
                FROM agent.events
                WHERE task_id = $1
                ORDER BY event_seq ASC
                """,
                task_id,
            )
            events = [
                _event_adapter.validate_python(_json_loads(row["event_json"]))
                for row in event_rows
            ]

        pending_approval_id = None
        if plan is not None:
            paused_step = next(
                (step for step in plan.steps if step.status == ExecutionStatus.PAUSED),
                None,
            )
            if (
                paused_step is not None
                and paused_step.result is not None
                and isinstance(paused_step.result.data, dict)
            ):
                pending_approval_id = paused_step.result.data.get("approval_id")

        return Task(
            id=str(task_row["id"]),
            message=task_row["message"],
            status=TaskStatus(task_row["status"]),
            plan=plan,
            events=events,
            summary=task_row["summary"],
            error=task_row["error"],
            pending_approval_id=pending_approval_id,
            created_at=task_row["created_at"],
            updated_at=task_row["updated_at"],
        )

    async def list_all_tasks(self) -> list[Task]:
        pool = await get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id
                FROM agent.tasks
                ORDER BY created_at DESC
                """
            )

        tasks: list[Task] = []
        for row in rows:
            task = await self.get_task_by_id(str(row["id"]))
            if task is not None:
                tasks.append(task)

        return tasks

    async def delete(self, task_id: str) -> bool:
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM agent.tasks WHERE id = $1",
                task_id,
            )

        return not result.endswith(" 0")

    async def _upsert_task(self, conn, task: Task) -> None:
        await conn.execute(
            """
            INSERT INTO agent.tasks (
                id, message, status, summary, error, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (id) DO UPDATE SET
                message = EXCLUDED.message,
                status = EXCLUDED.status,
                summary = EXCLUDED.summary,
                error = EXCLUDED.error,
                updated_at = EXCLUDED.updated_at
            """,
            task.id,
            task.message,
            task.status.value,
            task.summary,
            task.error,
            task.created_at,
            task.updated_at,
        )

    async def _upsert_plan(self, conn, task_id: str, plan: Plan) -> None:
        await conn.execute(
            """
            INSERT INTO agent.plans (
                id, task_id, title, goal, language, message,
                status, result, error, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, now(), now())
            ON CONFLICT (id) DO UPDATE SET
                task_id = EXCLUDED.task_id,
                title = EXCLUDED.title,
                goal = EXCLUDED.goal,
                language = EXCLUDED.language,
                message = EXCLUDED.message,
                status = EXCLUDED.status,
                result = EXCLUDED.result,
                error = EXCLUDED.error,
                updated_at = now()
            """,
            plan.id,
            task_id,
            plan.title,
            plan.goal,
            plan.language,
            plan.message,
            plan.status.value,
            plan.result,
            plan.error,
        )

    async def _sync_steps(self, conn, task_id: str, plan: Plan) -> None:
        current_step_ids = [step.id for step in plan.steps]

        for index, step in enumerate(plan.steps, start=1):
            await self._upsert_step(conn, task_id, plan.id, index, step)

        await self._delete_removed_steps(conn, plan.id, current_step_ids)

    async def _upsert_step(
        self,
        conn,
        task_id: str,
        plan_id: str,
        step_order: int,
        step: Step,
    ) -> None:
        await conn.execute(
            """
            INSERT INTO agent.steps (
                id, plan_id, task_id, step_order, description,
                tool_name, tool_arguments, status, result, error,
                success, reason, attachments, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, $11, $12, $13::jsonb, now(), now())
            ON CONFLICT (id) DO UPDATE SET
                plan_id = EXCLUDED.plan_id,
                task_id = EXCLUDED.task_id,
                step_order = EXCLUDED.step_order,
                description = EXCLUDED.description,
                tool_name = EXCLUDED.tool_name,
                tool_arguments = EXCLUDED.tool_arguments,
                status = EXCLUDED.status,
                result = EXCLUDED.result,
                error = EXCLUDED.error,
                success = EXCLUDED.success,
                reason = EXCLUDED.reason,
                attachments = EXCLUDED.attachments,
                updated_at = now()
            """,
            step.id,
            plan_id,
            task_id,
            step_order,
            step.description,
            step.tool_name,
            json.dumps(step.tool_arguments, ensure_ascii=False),
            step.status.value,
            _step_result_to_db(step.result),
            step.error,
            step.success,
            step.reason,
            json.dumps(step.attachments, ensure_ascii=False),
        )

    async def _delete_removed_steps(
        self,
        conn,
        plan_id: str,
        current_step_ids: list[str],
    ) -> None:
        if current_step_ids:
            await conn.execute(
                """
                DELETE FROM agent.steps
                WHERE plan_id = $1
                AND NOT (id = ANY($2::uuid[]))
                """,
                plan_id,
                current_step_ids,
            )
            return

        await conn.execute(
            "DELETE FROM agent.steps WHERE plan_id = $1",
            plan_id,
        )
