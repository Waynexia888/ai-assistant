from typing import Any

from app.domain.models.tool import ToolDefinition, ToolParameter


def to_openai_tool_schema(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": _build_properties(tool),
                "required": tool.required,
                "additionalProperties": False,
            },
        },
    }


def _build_properties(tool: ToolDefinition) -> dict[str, Any]:
    return {
        parameter.name: _build_parameter_schema(parameter)
        for parameter in tool.parameters
    }


def _build_parameter_schema(parameter: ToolParameter) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": parameter.type,
    }

    if parameter.description:
        schema["description"] = parameter.description

    if parameter.enum:
        schema["enum"] = parameter.enum

    if parameter.default is not None:
        schema["default"] = parameter.default

    schema.update(parameter.metadata)
    return schema
