
from app.domain.models.plan import Plan, Step
from app.core.config import settings

from openai import AsyncOpenAI

from typing import Any
import json


class PlannerService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE or None,
        )
        self.model = settings.BASE_MODEL


    async def create_plan(self, message: str) -> Plan:
        """
        Create a structured Plan from the user's original message.

        Planner only plans.
        It does not execute steps.
        It does not call tools.
        """

        try:
            raw_text = await self._call_llm(message)
            data =self._parse_json(raw_text)

            # 过滤掉不符合规范的字段，保证数据质量。
            plan = Plan.model_validate(data)

            # 强制保留原始用户输入，避免模型乱改 message
            plan.message = message

            return plan


        except Exception as e:
            return self._fallback_plan(message, error=str(e))


    async def _call_llm(self, message: str) -> str:
        planner_prompt = self._build_planner_prompt()

        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": planner_prompt},
                {"role": "user", "content": message},
            ]
        )

        return response.choices[0].message.content or ""


    def _build_planner_prompt(self) -> str:
        return """
            You are a task planner.

            Your only job is to convert the user's request into a structured execution plan.

            Rules:
            1. Do not execute the task.
            2. Do not answer the user's question directly.
            3. Do not call tools.
            4. Break the task into 3 to 6 clear executable steps.
            5. Each step should be simple and actionable.
            6. Return JSON only.
            7. Do not use Markdown.
            8. Do not wrap the JSON in ```json.

            The JSON must follow this schema:

            {
                "title": "short task title",
                "goal": "the final goal of the user's task",
                "language": "zh",
                "message": "original user message",
                "steps": [
                            {
                                "description": "what this step should do"
                            }
                        ]
            }

            Important:
            - language should be "zh" if the user uses Chinese.
            - language should be "en" if the user uses English.
            - steps should not include result.
            - steps should not include success.
            - steps should not include status unless necessary.
            """.strip()
    
    def _parse_json(self, json_text: str) -> dict[str, Any]:
        """
        Parse LLM output into dict.

        First version uses json.loads.
        Later you can replace this with json-repair.
        """

        json_text = json_text.strip()

        if json_text.startswith("```json"):
            json_text = json_text.removeprefix("```json").strip()

        if json_text.startswith("```"):
            json_text = json_text.removeprefix("```").strip()

        if json_text.endswith("```"):
            json_text = json_text.removesuffix("```").strip()

        return json.loads(json_text)
    

    def _fallback_plan(self, message: str, error: str | None = None) -> Plan:
        """
        If LLM planning fails, create a simple runnable plan.
        This guarantees the task pipeline can continue.
        """

        return Plan(
            title="通用任务计划",
            goal=message,
            language="zh",
            message=message,
            steps=[
                Step(description="理解用户的任务目标"),
                Step(description="拆解任务需要完成的关键步骤"),
                Step(description="按照步骤执行任务并整理结果"),
            ],
            error=error,
        )