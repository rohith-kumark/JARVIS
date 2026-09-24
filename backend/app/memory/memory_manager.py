"""Memory manager for short-term contextual memory and user preferences."""

import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.db.models import Memory, UserPreference

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages short-term contextual memory entries and user preferences in SQLite."""

    def set_memory(
        self,
        db: Session,
        key: str,
        value: str,
        conversation_id: Optional[str] = None,
        memory_type: str = "short_term",
    ) -> Memory:
        """Store or update a memory item."""
        query = db.query(Memory).filter(Memory.key == key)
        if conversation_id:
            query = query.filter(Memory.conversation_id == conversation_id)
        else:
            query = query.filter(Memory.conversation_id.is_(None))

        existing = query.first()
        if existing:
            existing.value = value
            existing.memory_type = memory_type
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated memory '{key}' for conv='{conversation_id}'")
            return existing

        new_mem = Memory(
            key=key,
            value=value,
            conversation_id=conversation_id,
            memory_type=memory_type,
        )
        db.add(new_mem)
        db.commit()
        db.refresh(new_mem)
        logger.info(f"Created memory '{key}' for conv='{conversation_id}'")
        return new_mem

    def get_memories(
        self, db: Session, conversation_id: Optional[str] = None
    ) -> List[Memory]:
        """Fetch memories for a conversation, including global memories."""
        filters = []
        if conversation_id:
            filters.append(
                or_(
                    Memory.conversation_id == conversation_id,
                    Memory.conversation_id.is_(None),
                )
            )
        else:
            filters.append(Memory.conversation_id.is_(None))

        return db.query(Memory).filter(*filters).order_by(Memory.updated_at.desc()).all()

    def set_preference(self, db: Session, key: str, value: str) -> UserPreference:
        """Store or update a user preference."""
        pref = db.query(UserPreference).filter(UserPreference.key == key).first()
        if pref:
            pref.value = value
            db.commit()
            db.refresh(pref)
            return pref

        new_pref = UserPreference(key=key, value=value)
        db.add(new_pref)
        db.commit()
        db.refresh(new_pref)
        return new_pref

    def get_preferences(self, db: Session) -> Dict[str, str]:
        """Fetch all user preferences as a dictionary."""
        rows = db.query(UserPreference).all()
        return {r.key: r.value for r in rows}

    def build_context_prompt(self, db: Session, conversation_id: Optional[str] = None) -> str:
        """Construct a formatted contextual memory block for LLM system context."""
        memories = self.get_memories(db, conversation_id)
        preferences = self.get_preferences(db)

        if not memories and not preferences:
            return ""

        context_lines = ["\n[Contextual Memory & User Preferences]"]
        if preferences:
            context_lines.append("User Preferences:")
            for k, v in preferences.items():
                context_lines.append(f"- {k}: {v}")

        if memories:
            context_lines.append("Short-term Memory Context:")
            for m in memories:
                scope = f"(Conv: {m.conversation_id[:8]})" if m.conversation_id else "(Global)"
                context_lines.append(f"- {m.key}: {m.value} {scope}")

        return "\n".join(context_lines)


# Global memory manager instance
memory_manager = MemoryManager()
