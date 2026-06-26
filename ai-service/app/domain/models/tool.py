from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ToolParameterType = Literal["string", "number", "integer", "boolean", "object", "array"]



class ToolParameter(BaseModel):
    name: str
    type: ToolParameterType = "string"
    description: str = ""
    required: bool = True
    enum: list[str] | None = None
    default: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: list[ToolParameter] = Field(default_factory=list)
    required: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_required_parameters(self) -> "ToolDefinition":
        if "required" in self.model_fields_set:
            required_names = set(self.required)
            for parameter in self.parameters:
                parameter.required = parameter.name in required_names
        else:
            self.required = [
                parameter.name
                for parameter in self.parameters
                if parameter.required
            ]

        return self

    @property
    def parameters_by_name(self) -> dict[str, ToolParameter]:
        return {
            parameter.name: parameter
            for parameter in self.parameters
        }
