from pydantic import BaseModel, Field
from typing import Literal


ToolParameterType = Literal["string", "number", "integer", "boolean", "object", "array"]



class ToolParameter(BaseModel):
    name: str
    type: ToolParameterType = "string"
    description: str = ""
    required: bool = True


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: list[ToolParameter] = Field(default_factory=list)