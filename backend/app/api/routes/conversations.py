"""Conversations API router."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.exceptions import ConversationNotFoundError
from backend.app.db.session import get_db
from backend.app.memory.conversation_manager import conversation_manager
from backend.app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    MessageRead,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


@router.get("", response_model=List[ConversationSummary])
def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[ConversationSummary]:
    """Retrieve list of past conversations."""
    conversations = conversation_manager.list_conversations(db, limit=limit)
    result = []
    for conv in conversations:
        result.append(
            ConversationSummary(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=len(conv.messages),
            )
        )
    return result


@router.post("", response_model=ConversationSummary)
def create_conversation(
    payload: ConversationCreate = None,
    db: Session = Depends(get_db),
) -> ConversationSummary:
    """Explicitly create a new conversation session."""
    title = payload.title if payload else "New Conversation"
    conv = conversation_manager.create_conversation(db, title=title)
    return ConversationSummary(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=0,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    """Retrieve a conversation session and all its messages."""
    try:
        conv = conversation_manager.get_conversation(db, conversation_id)
        messages = conversation_manager.get_messages(db, conversation_id)
        return ConversationDetail(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=[MessageRead.model_validate(m) for m in messages],
        )
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Delete a conversation and all its messages."""
    try:
        conversation_manager.delete_conversation(db, conversation_id)
        return {"status": "success", "message": f"Conversation {conversation_id} deleted"}
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
