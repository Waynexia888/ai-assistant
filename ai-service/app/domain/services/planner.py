
from app.domain.models.plan import Plan, Step
from app.domain.tools.registry import ToolRegistry
from app.domain.tools.builtin import create_builtin_tool_registry
from app.domain.tools.policy import (
    BROWSER_OBSERVATION_TOOL_NAMES,
    BROWSER_APPROVAL_ACTION_TOOL_NAMES,
    BROWSER_BLOCKED_ACTION_TOOL_NAMES,
    DEFAULT_AUTO_TOOL_RISK_LEVELS,
    DEFAULT_LLM_TOOL_CALLING_ALLOWED_TOOLS,
)
from app.core.config import settings
from app.skills.loader import SkillLoader

from openai import AsyncOpenAI

from typing import Any
import json
import re


LLM_TOOL_CALLING_TOOL_NAME = "llm_tool_calling"


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
        tools_text = self._build_available_tools_text()
        rag_planning_skill = self.skill_loader.load("rag_planning")

        return f"""
            You are a task planner.

            Your only job is to convert the user's request into a structured execution plan.

            Use llm_tool_calling when the task needs information from the local knowledge base and asks for a final answer.
            Allow the runtime to call rag_search inside llm_tool_calling for knowledge-base answer tasks.
            Use fixed rag_search only when the user explicitly asks to retrieve/search/list raw chunks instead of answering.
            Do not use rag_search for simple translation, rewriting, formatting, calculation, or brainstorming.
            Do not plan add_urls in this phase because add_urls is not registered as an available tool yet.
            When planning knowledge-base search, preserve exact names, titles, identifiers, punctuation, slashes, ampersands, and distinctive source-language keywords in query_hint.
            Use tool_name="llm_tool_calling" when a step needs the runtime LLM to decide which tools to call during execution.
            Use a fixed tool_name such as "rag_search" when the step is a simple single-tool operation.
            Do not use llm_tool_calling for simple translation, formatting, or calculation unless a tool is clearly needed.
            
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
            6. For llm_tool_calling, tool_arguments must include allowed_tools. For knowledge-base tasks, include query_hint with exact user-provided target text.
            7. Use 1 to 3 clear executable steps. For a simple one-tool task, use exactly 1 step.
            8. Prefer fixed tools for simple one-tool work, except knowledge-base answer tasks should prefer llm_tool_calling with allowed_tools=["rag_search"].
            9. Return JSON only.
            10. Do not use Markdown.
            11. title must name the concrete target when the user gives one.
            12. goal must describe the exact final answer the user wants, not a vague action like "get details".
            13. Read-only browser tools are: {BROWSER_OBSERVATION_TOOL_NAMES}.
            14. Plan an approval-gated browser action only when the user explicitly asks for that exact action: {BROWSER_APPROVAL_ACTION_TOOL_NAMES}.
            15. Never plan blocked browser actions in this phase: {BROWSER_BLOCKED_ACTION_TOOL_NAMES}.
            16. When the user provides a URL and asks to observe, inspect, summarize, or screenshot the page, plan browser.open with that URL before browser.observe or browser.screenshot.
            17. browser.observe observes the current page and does not accept a URL. Put the URL only in browser.open tool_arguments.
            18. For browser.click and browser.type, do not invent CSS selectors or DOM ids. Use semantic visible targets such as element="Create my account link", role="link", or element="Log In button".
            19. If the user explicitly provides a CSS selector for a browser action, preserve it in selector, but also set element to the clearest human-readable target when possible.

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
                        "tool_name": "llm_tool_calling",
                        "tool_arguments": {{
                            "allowed_tools": ["rag_search"],
                            "query_hint": "Good Shampoo/Conditioner / 4 stars / conditioner leaked"
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

            Example browser.click step:
            {{
                "description": "Click the Create my account link",
                "tool_name": "browser.click",
                "tool_arguments": {{
                    "element": "Create my account link",
                    "role": "link"
                }},
                "reason": "The user explicitly asked to click the Create my account link."
            }}

            Example llm_tool_calling step:
            {{
                "description": "Use available tools as needed to gather evidence and answer the user's question",
                "tool_name": "llm_tool_calling",
                "tool_arguments": {{
                    "allowed_tools": ["rag_search"],
                    "query_hint": "exact title or identifier plus distinctive source-language keywords"
                }},
                "reason": "This step may require the runtime LLM to decide whether and how to search the knowledge base before producing the answer."
            }}



            Important:
            - language should be "zh" if the user uses Chinese.
            - language should be "en" if the user uses English.
            - steps should not include result.
            - steps should not include success.
            - steps should not include status unless necessary.
            """.strip()


    def _normalize_plan(self, plan: Plan) -> None:
        self._normalize_browser_steps(plan)

        for step in plan.steps:
            if self._should_upgrade_rag_step_to_runtime(plan, step):
                self._upgrade_rag_step_to_runtime(step)

            if step.tool_name == "rag_search" and not step.reason:
                step.reason = "用户请求需要基于本地知识库证据回答。"

            if step.tool_name == LLM_TOOL_CALLING_TOOL_NAME:
                self._normalize_llm_tool_calling_step(step)

    def _normalize_browser_steps(self, plan: Plan) -> None:
        self._remove_unrequested_browser_actions(plan)
        url = self._extract_first_url(plan.message)
        if url is None:
            return

        browser_steps = [
            step
            for step in plan.steps
            if step.tool_name in {
                *BROWSER_OBSERVATION_TOOL_NAMES,
                *BROWSER_APPROVAL_ACTION_TOOL_NAMES,
            }
        ]
        if not browser_steps:
            return

        normalized_steps: list[Step] = []
        page_opened = False

        for step in plan.steps:
            if step.tool_name == "browser.open":
                step.tool_arguments = {
                    **step.tool_arguments,
                    "url": step.tool_arguments.get("url") or url,
                }
                page_opened = True
                normalized_steps.append(step)
                continue

            if (
                step.tool_name in {
                    "browser.observe",
                    "browser.screenshot",
                    "browser.extract_links",
                    *BROWSER_APPROVAL_ACTION_TOOL_NAMES,
                }
                and not page_opened
            ):
                normalized_steps.append(
                    Step(
                        description=f"打开网页 {url}",
                        tool_name="browser.open",
                        tool_arguments={"url": url},
                        reason="后续浏览器观察工具需要先打开用户指定的网页。",
                    )
                )
                page_opened = True

            if step.tool_name in {
                "browser.observe",
                "browser.screenshot",
                "browser.extract_links",
                *BROWSER_APPROVAL_ACTION_TOOL_NAMES,
            }:
                step.tool_arguments.pop("url", None)

            normalized_steps.append(step)

        if (
            page_opened
            and not any(
                step.tool_name == "browser.observe"
                for step in normalized_steps
            )
            and self._message_requests_browser_observation(plan.message)
        ):
            normalized_steps.append(
                Step(
                    description="观察当前网页内容",
                    tool_name="browser.observe",
                    tool_arguments={},
                    reason="用户要求观察或总结网页，需要读取打开后的页面内容。",
                )
            )

        plan.steps = normalized_steps[:3]

    def _remove_unrequested_browser_actions(self, plan: Plan) -> None:
        message = plan.message.lower()
        action_markers = {
            "browser.click": ["点击", "点按", "click", "press the button"],
            "browser.type": ["输入", "填写", "键入", "type", "fill"],
        }

        safe_steps: list[Step] = []
        for step in plan.steps:
            if step.tool_name in BROWSER_BLOCKED_ACTION_TOOL_NAMES:
                continue
            markers = action_markers.get(step.tool_name)
            if markers is not None and not any(marker in message for marker in markers):
                continue
            safe_steps.append(step)
        plan.steps = safe_steps

    def _extract_first_url(self, message: str) -> str | None:
        match = re.search(r"https?://[^\s，。！？,;]+", message)
        if match is None:
            return None
        return match.group(0).rstrip("'\"、）)]}")

    def _message_requests_browser_observation(self, message: str) -> bool:
        normalized = message.lower()
        markers = [
            "观察",
            "查看",
            "总结",
            "网页内容",
            "是什么网站",
            "observe",
            "inspect",
            "summarize",
            "what site",
        ]
        return any(marker in normalized for marker in markers)

    def _should_upgrade_rag_step_to_runtime(self, plan: Plan, step: Step) -> bool:
        if step.tool_name != "rag_search":
            return False

        message = plan.message.lower()
        answer_markers = [
            "根据知识库回答",
            "为什么",
            "解释",
            "回答",
            "请引用",
            "answer",
            "why",
            "explain",
        ]
        raw_search_markers = [
            "只检索",
            "只搜索",
            "列出 chunks",
            "返回 chunks",
            "raw chunks",
            "search only",
            "retrieve only",
        ]

        if any(marker in message for marker in raw_search_markers):
            return False

        return any(marker in message for marker in answer_markers)

    def _upgrade_rag_step_to_runtime(self, step: Step) -> None:
        original_arguments = dict(step.tool_arguments)
        query_hint = original_arguments.get("query") or original_arguments.get("query_hint")
        top_k = original_arguments.get("top_k")

        step.tool_name = LLM_TOOL_CALLING_TOOL_NAME
        step.tool_arguments = {
            "allowed_tools": ["rag_search"],
        }

        if query_hint:
            step.tool_arguments["query_hint"] = query_hint
        if top_k:
            step.tool_arguments["top_k"] = top_k


    def _normalize_llm_tool_calling_step(self, step: Step) -> None:
        allowed_tools = step.tool_arguments.get("allowed_tools")

        if not isinstance(allowed_tools, list) or not allowed_tools:
            registered_tools = set(self.tool_registry.list_tools(risk_levels=DEFAULT_AUTO_TOOL_RISK_LEVELS))
            step.tool_arguments["allowed_tools"] = [
                tool_name
                for tool_name in DEFAULT_LLM_TOOL_CALLING_ALLOWED_TOOLS
                if tool_name in registered_tools
            ]

        if not step.reason:
            step.reason = (
                "这个步骤需要在执行过程中由 LLM 根据上下文动态决定是否调用工具。"
            )


    def _build_available_tools_text(self) -> str:
        tool_definitions = self.tool_registry.list_tool_definitions()
        tools = [
            self._format_tool_definition(tool)
            for tool in tool_definitions
        ]
        tools.append(self._format_llm_tool_calling_definition())

        return "\n".join(tools)


    def _format_llm_tool_calling_definition(self) -> str:
        registered_tools = set(self.tool_registry.list_tools(risk_levels=DEFAULT_AUTO_TOOL_RISK_LEVELS))
        allowed_tools = [
            tool_name
            for tool_name in DEFAULT_LLM_TOOL_CALLING_ALLOWED_TOOLS
            if tool_name in registered_tools
        ]

        return (
            f"- {LLM_TOOL_CALLING_TOOL_NAME}: Let the runtime LLM decide which allowed tools to call during execution.\n"
            f"  parameters:\n"
            f"    - allowed_tools: array, required, Allowed tool names for this runtime step. "
            f"Recommended safe tools now: {allowed_tools}"
        )


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
