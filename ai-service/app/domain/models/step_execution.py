from pydantic import BaseModel, Field

from app.domain.models.event import Event


class StepExecutionResult(BaseModel):
    error: str | None = None
    events: list[Event] = Field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.error is None
