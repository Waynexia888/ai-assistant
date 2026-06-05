from pydantic import BaseModel, Field
import uuid
from typing import List, Optional
from enum import Enum



class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    

class Step(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    success: bool = False
    # 这个步骤执行过程中产生的附件、文件、截图、报告、图片、代码文件等资源列表。
    attachments: List[str] = Field(default_factory=list)


    @property
    def done(self) -> bool:
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]
    

class Plan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    goal: str = ""
    language: str = "zh"
    message: str = ""
    steps: List[Step] = Field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None

    @property
    def done(self) -> bool:
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]

    def get_next_step(self) -> Optional[Step]:
        return next((step for step in self.steps if not step.done), None)