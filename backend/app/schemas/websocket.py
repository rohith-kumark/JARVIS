from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class WebSocketEventType(str, Enum):
    # System events
    CONNECTION_ACK = "connection_ack"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

    # Agent interaction events
    USER_MESSAGE = "user_message"
    AGENT_THINKING = "agent_thinking"
    TOOL_START = "tool_start"
    TOOL_COMPLETE = "tool_complete"
    AGENT_MESSAGE = "agent_message"


class WebSocketInboundMessage(BaseModel):
    type: WebSocketEventType
    payload: Dict[str, Any] = Field(default_factory=dict)


class WebSocketOutboundMessage(BaseModel):
    type: WebSocketEventType
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return self.model_dump_json()
