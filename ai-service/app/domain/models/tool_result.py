from pydantic import BaseModel, Field
from typing import Any, Optional, TypeVar, Generic

T = TypeVar('T')


class ToolResult(BaseModel, Generic[T]):
    success: bool = True           # 是否成功调用
    message: Optional[str] = None  #放额外说明，比如错误信息、提示信息。
    data: Optional[T] = None       # 工具的执行结果/数据
    metadata: dict[str, Any] = Field(default_factory=dict)
