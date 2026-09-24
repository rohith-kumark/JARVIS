from typing import Any, Dict, Optional


class JarvisBaseException(Exception):
    """Base exception for all JARVIS errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class LLMException(JarvisBaseException):
    """Base exception for LLM operations."""
    pass


class LLMAuthenticationError(LLMException):
    """Raised when LLM API authentication fails."""
    pass


class LLMProviderUnavailableError(LLMException):
    """Raised when LLM provider is offline or unreachable."""
    pass


class ToolException(JarvisBaseException):
    """Base exception for tool execution errors."""
    pass


class ToolNotFoundError(ToolException):
    """Raised when a requested tool does not exist in registry."""
    pass


class ToolExecutionError(ToolException):
    """Raised when an error occurs during tool execution."""
    pass


class ToolPermissionDeniedError(ToolException):
    """Raised when user does not have required permission to execute tool."""
    pass


class ToolValidationError(ToolException):
    """Raised when input parameters fail schema validation."""
    pass
