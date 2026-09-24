"""Tool interface and base abstraction for JARVIS."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class ToolProtocol(Protocol):
    """Protocol defining the expected interface for all JARVIS tools."""

    name: str
    description: str
    parameters: Dict[str, Any]

    def execute(self, **kwargs: Any) -> Any:
        """Execute the tool synchronously with validated arguments."""
        ...


class BaseTool(ABC):
    """Abstract base class providing standard properties and metadata for tools."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Execute tool logic. Must be implemented by concrete tool classes."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Export tool metadata dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
