from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True

    async def __call__(self, **kwargs: Any) -> Any:
        """Execute the tool with given parameters."""
        return await self.execute(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict[str, Any]:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self) -> bool:
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult") -> "ToolResult":
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ) -> Optional[str]:
            if field and other_field:
                if concatenate:
                    return field + other_field  # type: ignore
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self) -> str:
        return f"Error: {self.error}" if self.error else repr(self.output)

    def replace(self, **kwargs: Any) -> "ToolResult":
        """Returns a new ToolResult with the given fields replaced."""
        return type(self)(**{**self.dict(), **kwargs})


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""


class AgentAwareTool:
    agent: Optional[Any] = None
