from langchain_openai import ChatOpenAI
from app.core.config import settings


def get_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.BASE_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE or None,
        temperature=0.3,
    )


async def run_langchain_agent(user_input: str) -> str:
    llm = get_chat_model()

    response = await llm.ainvoke(user_input)

    return str(response.content)