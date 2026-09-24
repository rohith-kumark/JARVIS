"""Conversation manager for managing sessions and message history."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.exceptions import ConversationNotFoundError
from backend.app.db.models import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages lifecycle of conversations and messages in SQLite/SQLAlchemy."""

    def create_conversation(self, db: Session, title: Optional[str] = None) -> Conversation:
        """Create a new conversation session."""
        conversation = Conversation(title=title or "New Conversation")
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        logger.info(f"Created conversation: {conversation.id} ('{conversation.title}')")
        return conversation

    def get_conversation(self, db: Session, conversation_id: str) -> Conversation:
        """Fetch conversation by ID or raise ConversationNotFoundError."""
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise ConversationNotFoundError(f"Conversation with ID '{conversation_id}' not found")
        return conversation

    def get_or_create_conversation(self, db: Session, conversation_id: Optional[str] = None) -> Conversation:
        """Fetch existing conversation or create a new one if not found or not specified."""
        if conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                return conv
        return self.create_conversation(db)

    def list_conversations(self, db: Session, limit: int = 50) -> List[Conversation]:
        """List recent conversations ordered by updated_at descending."""
        return (
            db.query(Conversation)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .all()
        )

    def add_message(
        self,
        db: Session,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Append a message to a conversation session."""
        conv = self.get_conversation(db, conversation_id)
        now = datetime.now(timezone.utc)
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_json=json.dumps(metadata) if metadata else None,
            created_at=now,
        )
        db.add(msg)
        # Update conversation timestamp and set title if default
        conv.updated_at = now
        if conv.title == "New Conversation" and role == "user":
            # Set summary title from first user query (up to 50 chars)
            first_line = content.strip().split("\n")[0]
            conv.title = (first_line[:47] + "...") if len(first_line) > 50 else first_line

        db.commit()
        db.refresh(msg)
        return msg

    def get_messages(
        self, db: Session, conversation_id: str, limit: Optional[int] = None
    ) -> List[Message]:
        """Fetch messages for a conversation ordered chronologically."""
        query = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    def delete_conversation(self, db: Session, conversation_id: str) -> bool:
        """Delete a conversation and all cascaded children."""
        conv = self.get_conversation(db, conversation_id)
        db.delete(conv)
        db.commit()
        logger.info(f"Deleted conversation: {conversation_id}")
        return True


# Global conversation manager instance
conversation_manager = ConversationManager()
