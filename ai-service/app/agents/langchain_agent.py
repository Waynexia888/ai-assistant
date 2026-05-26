from typing import Literal, Optional, List, Any

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from app.core.config import settings
from app.prompts.agent_prompts import AgentPromptBuilder
from app.emotions.emotion_service import EmotionClass
from app.middleware.emotion_middleware import EmotionMiddleware


AgentMode = Literal["basic", "deep"]


class LangChainAgent:
    def __init__(self, mode: AgentMode = "basic"):
        self.mode = mode
        self.model = self._get_chat_model()
        self.tools = self._get_tools()
        self.emotion_service = EmotionClass(model=settings.BASE_MODEL)
        self.agent = self._build_agent()
    
    def _get_chat_model(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=settings.BASE_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE or None,
            temperature=0.3,
        )
    
    def _get_tools(self) -> list:
        return [
            # rag_search_tool,
            # web_search_tool,
        ]
    
    def _build_agent(self):
        if self.mode == "deep":
            return self._build_deep_agent()
        
        return self._build_basic_agent()
    
    def _build_basic_agent(self):
        """
        Phase 1:
        Basic LangChain tool-calling agent.
        Used for chat, RAG, web search, and simple tool execution.
        """

        return create_agent(
            model=self.model,
            tools=self.tools,
            middleware=[
                EmotionMiddleware(
                    emotion_service=self.emotion_service
                )
            ],
        )

    def _build_deep_agent(self):
        """
        Phase 2:
        DeepAgent runtime for long-running, multi-step tasks.
        Used for report generation, document analysis, task planning,
        and file-system-like context management.
        """
        raise NotImplementedError("DeepAgent mode is not implemented yet.")



    
    async def run(
        self, 
        message: str, 
        session_id: str,
        history: Optional[List[dict[str, str]]] = None,
        feeling: Optional[dict[str, Any]] = None
        ) -> str:

        messages: list[dict[str, str]] = []

        if history:
            messages.extend(history)

        messages.append({
            "role": "user",
            "content": message,
        })

        input_state: dict[str, Any] = {
            "messages": messages,
        }

        # 如果外部已经识别过情绪，也可以直接传进 state
        # middleware 会优先使用这个 feeling，不会重复识别
        if feeling:
            input_state["feeling"] = feeling
            
        # print("===== Agent input_state =====")
        # print(input_state)
        # print("=============================")

        result = await self.agent.ainvoke(
            input_state,
            config={
                "configurable": {
                    "thread_id": session_id,
                    "session_id": session_id,
                }
            }
        )

        return self._extract_answer(result)
    


    def _extract_answer(self, result: Any) -> str:
        messages = result.get("messages", [])

        if not messages:
            return ""
        
        last_message = messages[-1]
        return getattr(last_message, "content", str(last_message))
