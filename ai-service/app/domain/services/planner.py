
from app.domain.models.plan import Plan, Step
from app.domain.tools.registry import ToolRegistry
from app.domain.tools.builtin import create_builtin_tool_registry
from app.core.config import settings
from app.skills.loader import SkillLoader

from openai import AsyncOpenAI

from typing import Any
import json


class PlannerService:
    def __init__(
        self, 
        tool_registry: ToolRegistry | None = None,
        skill_loader: SkillLoader | None = None,
    ):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE or None,
        )
        self.model = settings.BASE_MODEL
        self.tool_registry = tool_registry or create_builtin_tool_registry()
        self.skill_loader = skill_loader or SkillLoader()


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
            self._normalize_plan(plan)

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
        tool_definitions = self.tool_registry.list_tool_definitions()
        tools_text = "\n".join(
            self._format_tool_definition(tool)
            for tool in tool_definitions
        )
        rag_planning_skill = self.skill_loader.load("rag_planning")

        return f"""
            You are a task planner.

            Your only job is to convert the user's request into a structured execution plan.

            Use rag_search when the task needs information from the local knowledge base.
            Do not use rag_search for simple translation, rewriting, formatting, calculation, or brainstorming.
            Do not plan add_urls in this phase because add_urls is not registered as an available tool yet.
            When planning rag_search, preserve exact names, titles, identifiers, and distinctive source-language keywords in the query.
            
            RAG planning policy:
            {rag_planning_skill}

            Available tools:
            {tools_text}

            Rules:
            1. Do not execute the task.
            2. Do not answer the user's question directly.
            3. Choose exactly one tool for each step.
            4. tool_name must be one of the available tool names.
            5. tool_arguments must match the chosen tool.
            6. Use 1 to 3 clear executable steps. For a simple one-tool task, use exactly 1 step.
            7. Return JSON only.
            8. Do not use Markdown.
            9. title must name the concrete target when the user gives one.
            10. goal must describe the exact final answer the user wants, not a vague action like "get details".

            The JSON must follow this schema:

            {{
                "title": "short task title naming the concrete target",
                "goal": "the exact final answer the user wants",
                "language": "zh",
                "message": "original user message",
                "steps": [
                            {{
                                "description": "what this step should do",
                                "tool_name": "one_of_available_tool_names",
                                "tool_arguments": {{
                                    "argument_name": "argument value"
                                }},
                                "reason": "why this tool is needed"
                            }}
                        ]
            }}

            Example rag_search step:
            {{
                "title": "检索目标评论并解释评分原因",
                "goal": "从知识库中找到 Good Shampoo/Conditioner 的匹配 review，并基于原文解释为什么只给 4 stars",
                "language": "zh",
                "message": "根据知识库回答：Good Shampoo/Conditioner 这条 review 为什么只给 4 stars？请引用原文证据。",
                "steps": [
                    {{
                        "description": "检索 Good Shampoo/Conditioner 的 4 stars review 原文证据",
                        "tool_name": "rag_search",
                        "tool_arguments": {{
                            "query": "Good Shampoo/Conditioner / 4 stars / conditioner leaked",
                            "top_k": 5
                        }},
                        "reason": "用户要求根据知识库解释指定 review 的评分原因，并要求引用原文证据。"
                    }}
                ]
            }}

            Generic rag_search step shape:
            {{
                "description": "Search the local knowledge base for information relevant to the user's question",
                "tool_name": "rag_search",
                "tool_arguments": {{
                    "query": "exact title or identifier plus distinctive source-language keywords",
                    "top_k": 5
                }},
                "reason": "The user asks for information that should be answered from the local knowledge base."
            }}



            Important:
            - language should be "zh" if the user uses Chinese.
            - language should be "en" if the user uses English.
            - steps should not include result.
            - steps should not include success.
            - steps should not include status unless necessary.
            """.strip()


    def _normalize_plan(self, plan: Plan) -> None:
        for step in plan.steps:
            if step.tool_name == "rag_search" and not step.reason:
                step.reason = "用户请求需要基于本地知识库证据回答。"


    def _format_tool_definition(self, tool) -> str:
        if not tool.parameters:
            return f"- {tool.name}: {tool.description}\n  parameters: none"

        parameters_text = "\n".join(
            f"    - {parameter.name}: {parameter.type}, "
            f"{'required' if parameter.required else 'optional'}, "
            f"{parameter.description}"
            for parameter in tool.parameters
        )

        return (
            f"- {tool.name}: {tool.description}\n"
            f"  parameters:\n"
            f"{parameters_text}"
        )
    
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
                Step(
                    description="理解用户的任务目标",
                    tool_name="echo",
                    tool_arguments={"text": "理解用户的任务目标"},
                ),
                Step(
                    description="拆解任务需要完成的关键步骤",
                    tool_name="echo",
                    tool_arguments={"text": "拆解任务需要完成的关键步骤"},
                ),
                Step(
                    description="按照步骤执行任务并整理结果",
                    tool_name="echo",
                    tool_arguments={"text": "按照步骤执行任务并整理结果"},
                ),
                        ],
            error=error,
        )
