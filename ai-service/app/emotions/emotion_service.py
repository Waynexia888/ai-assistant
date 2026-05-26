from typing import Literal, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings


class EmotionResult(BaseModel):
    feeling: Literal[
        "default",
        "upbeat",
        "angry",
        "cheerful",
        "depressed",
        "friendly",
    ] = Field(description="Detected user emotion")

    score: int = Field(
        ge=1,
        le=10,
        description="Negativity score from 1 to 10",
    )


class EmotionClass:
    def __init__(self, model: str | None = None):
        self.model = model or settings.BASE_MODEL
        self.chat_model = ChatOpenAI(model=self.model)
        self.emotion: Optional[EmotionResult] = None

    def sense(self, user_input: str) -> EmotionResult:
        if not user_input or not user_input.strip():
            return EmotionResult(feeling="default", score=5)

        text = self._truncate_input(user_input)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                    You are an emotion classification module.

                    Your task is to analyze the user's message and return a structured emotion result.

                    Scoring rules:
                    - The score must be an integer from 1 to 10.
                    - A higher score means stronger negative emotion.
                    - 1-3: positive, friendly, or cheerful emotion.
                    - 4-5: neutral or mild emotional fluctuation.
                    - 6-8: clearly negative emotion.
                    - 9-10: strongly negative emotion.

                    Emotion labels:
                    - default: neutral, calm, or ordinary message.
                    - upbeat: positive, motivated, or energetic.
                    - angry: angry, dissatisfied, frustrated, or blaming.
                    - cheerful: happy, joyful, or excited.
                    - depressed: sad, tired, discouraged, hopeless, or emotionally low.
                    - friendly: polite, thankful, warm, or friendly.

                    Classification guidelines:
                    1. Use "default" when the message is neutral or mostly informational.
                    2. Use "upbeat" when the user sounds motivated, proactive, or energetic.
                    3. Use "angry" when the user expresses anger, complaint, dissatisfaction, or frustration.
                    4. Use "cheerful" when the user expresses happiness, excitement, or joy.
                    5. Use "depressed" when the user sounds sad, exhausted, discouraged, or hopeless.
                    6. Use "friendly" when the user is polite, thankful, or socially warm.

                    Return only the structured output required by the schema.
                    """,
                ),
                ("user", "{input}"),
            ]
        )

        llm = self.chat_model.with_structured_output(EmotionResult)
        chain = prompt | llm

        try:
            result = chain.invoke({"input": text})
            self.emotion = result
            return result

        except Exception:
            return EmotionResult(feeling="default", score=5)

    def _truncate_input(self, user_input: str) -> str:
        if len(user_input) <= 300:
            return user_input

        return user_input[:150] + "\n...\n" + user_input[-150:]