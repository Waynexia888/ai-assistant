from pydantic import BaseModel
from typing import Optional, TypeVar, Generic

T = TypeVar('T')


class ToolResult(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None  #放额外说明，比如错误信息、提示信息。
    data: Optional[T] = None