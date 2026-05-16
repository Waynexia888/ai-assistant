from fastapi import APIRouter
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.agents.langchain_agent import run_langchain_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    answer = await run_langchain_agent(request.message)
    return ChatResponse(answer=answer)