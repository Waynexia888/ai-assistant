from openai import AsyncOpenAI

from app.core.config import settings


class DirectAnswerService:
    """Produces a final answer for simple conversational requests.

    This path intentionally does not create a plan and does not call tools.
    It is for greetings, identity questions, and ordinary chat that can be
    answered directly from the assistant persona.
    """

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE or None,
        )
        self.model = settings.BASE_MODEL

    async def answer(self, message: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant. Answer ordinary chat directly. "
                        "Do not mention tools, plans, internal steps, or execution. "
                        "Reply in the same language as the user. Keep the answer concise."
                    ),
                },
                {"role": "user", "content": message},
            ],
        )

        return response.choices[0].message.content or ""

