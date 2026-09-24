"""Domain exceptions for JARVIS AI assistant."""

from typing import Any, Dict, Optional


class JarvisBaseException(Exception):
    """Base exception for all JARVIS errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ToolExecutionError(JarvisBaseException):
    """Raised when a tool execution fails."""
    pass


class ToolSecurityError(JarvisBaseException):
    """Raised when tool execution violates security policies."""
    pass


class LLMServiceError(JarvisBaseException):
    """Raised when communication with the LLM provider fails."""
    pass


class ConversationNotFoundError(JarvisBaseException):
    """Raised when a requested conversation session does not exist."""
    pass


class MemoryError(JarvisBaseException):
    """Raised when memory retrieval or storage fails."""
    pass
