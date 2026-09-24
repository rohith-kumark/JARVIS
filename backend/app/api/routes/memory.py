"""Memory API router."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.memory.memory_manager import memory_manager
from backend.app.schemas.memory import MemoryItem, MemoryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memory", tags=["Memory"])


@router.get("", response_model=MemoryResponse)
def get_memory(
    conversation_id: Optional[str] = Query(None, description="Optional conversation ID to filter memory"),
    db: Session = Depends(get_db),
) -> MemoryResponse:
    """Retrieve memories and user preferences for context inspection."""
    memories = memory_manager.get_memories(db, conversation_id=conversation_id)
    preferences = memory_manager.get_preferences(db)

    return MemoryResponse(
        conversation_id=conversation_id,
        memories=[MemoryItem.model_validate(m) for m in memories],
        preferences=preferences,
    )
