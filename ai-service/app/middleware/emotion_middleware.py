from collections.abc import Callable, Awaitable
from typing import Any
from typing_extensions import NotRequired

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import SystemMessage

from app.prompts.agent_prompts import AgentPromptBuilder
from app.emotions.emotion_service import EmotionClass


class EmotionAgentState(AgentState):
    feeling: NotRequired[dict[str, Any]]


class EmotionMiddleware(AgentMiddleware[EmotionAgentState]):
    state_schema = EmotionAgentState

    def __init__(self, emotion_service: EmotionClass):
        super().__init__()
        self.emotion_service = emotion_service

    def before_model(
        self,
        state: EmotionAgentState,
        runtime,
    ) -> dict[str, Any] | None:
        if state.get("feeling"):
            return None

        messages = state.get("messages", [])
        latest_user_message = self._get_latest_user_message(messages)

        if not latest_user_message:
            return {
                "feeling": {
                    "feeling": "default",
                    "score": 5,
                }
            }

        emotion_result = self.emotion_service.sense(latest_user_message)

        return {
            "feeling": emotion_result.model_dump(),
        }

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        feeling = request.state.get(
            "feeling",
            {
                "feeling": "default",
                "score": 5,
            },
        )

        system_prompt = AgentPromptBuilder(
            feeling=feeling,
        ).build_system_prompt_text()

        new_system_message = SystemMessage(content=system_prompt)

        # print("===== EmotionMiddleware feeling =====")
        # print(feeling)
        # print("===== EmotionMiddleware system prompt =====")
        # print(system_prompt)
        # print("=========================================")

        return await handler(
            request.override(system_message=new_system_message)
        )

    def _get_latest_user_message(self, messages: list[Any]) -> str:
        for message in reversed(messages):
            role = None
            content = None

            if isinstance(message, dict):
                role = message.get("role")
                content = message.get("content")
            else:
                role = getattr(message, "type", None)
                content = getattr(message, "content", None)

            if role in {"user", "human"} and content:
                return str(content)

        return ""