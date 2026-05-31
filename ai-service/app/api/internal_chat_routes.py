# app/api/internal_chat_routes.py

from fastapi import APIRouter, HTTPException

from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.agents.langchain_agent import LangChainAgent
from app.emotions.emotion_service import EmotionClass

router = APIRouter(prefix="/internal/ai", tags=["Internal AI"])

agent = LangChainAgent(mode="basic")
emotion_service = EmotionClass()

@router.post("/chat", response_model=ChatResponse)
async def internal_chat(request: ChatRequest):
    try:
        session_id = request.session_id or "default"

        emotion_result = emotion_service.sense(request.message)

        feeling = emotion_result.model_dump()

        # print("Detected feeling:", feeling)

        # print("------------------------------")
        # print("Request:", request)
        # print("Request.history:", request.history)
        # print("------------------------------")

        answer = await agent.run(
            message=request.message,
            session_id=session_id,
            feeling=feeling,
            history=[message.model_dump() for message in request.history],
        )

        return ChatResponse(
            answer=answer,
            session_id=session_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat agent failed: {str(e)}",
        )
