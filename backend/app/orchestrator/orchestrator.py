"""JARVIS Core Orchestrator.

Orchestrates the entire intelligence flow:
React Frontend -> FastAPI Backend -> JARVIS Orchestrator -> Gemini LLM -> Tool Manager -> Python Tools
with Persistent Long-Term Memory (Phase 2).
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.llm.gemini_service import GeminiService, gemini_service
from backend.app.memory.conversation_manager import ConversationManager, conversation_manager
from backend.app.memory.manager import MemoryManager, memory_manager
from backend.app.schemas.chat import ChatResponse
from backend.app.tools.manager import ToolManager, tool_manager

logger = logging.getLogger(__name__)


class JarvisOrchestrator:
    """Coordinates conversations, persistent memory, LLM reasoning, and tool execution."""

    def __init__(
        self,
        llm: Optional[GeminiService] = None,
        conv_mgr: Optional[ConversationManager] = None,
        mem_mgr: Optional[MemoryManager] = None,
        tool_mgr: Optional[ToolManager] = None,
    ) -> None:
        self.llm = llm or gemini_service
        self.conv_mgr = conv_mgr or conversation_manager
        self.mem_mgr = mem_mgr or memory_manager
        self.tool_mgr = tool_mgr or tool_manager

    def process_message(
        self,
        user_message: str,
        conversation_id: Optional[str],
        db: Session,
    ) -> ChatResponse:
        """Process incoming user prompt through the complete orchestrator pipeline."""
        # 1. Resolve or create conversation session
        conv = self.conv_mgr.get_or_create_conversation(db, conversation_id)
        conv_id = conv.id

        # 2. Check for explicit memory control directives
        is_cmd, cmd_reply, _ = self.mem_mgr.handle_explicit_commands(user_message)
        if is_cmd and cmd_reply:
            self.conv_mgr.add_message(db=db, conversation_id=conv_id, role="user", content=user_message)
            self.conv_mgr.add_message(db=db, conversation_id=conv_id, role="assistant", content=cmd_reply)
            return ChatResponse(
                response=cmd_reply,
                conversation_id=conv_id,
                tool_calls=[],
                saved_memories=[],
            )

        # 3. Retrieve relevant long-term memories for the current user message
        memory_context, _ = self.mem_mgr.build_memory_context(user_message)

        # 4. Load past conversation messages for short-term dialog context
        past_messages = self.conv_mgr.get_messages(db, conv_id, limit=20)
        history = [{"role": msg.role, "content": msg.content} for msg in past_messages]

        # 5. Store incoming user message in database
        self.conv_mgr.add_message(
            db=db,
            conversation_id=conv_id,
            role="user",
            content=user_message,
        )

        # 6. Dispatch to Gemini reasoning engine (executing tools via ToolManager)
        response_text, tool_calls = self.llm.execute_chat_turn(
            user_message=user_message,
            conversation_history=history,
            context_prompt=memory_context,
            conversation_id=conv_id,
            db=db,
        )

        # 7. Secondary process: Automatic memory extraction (non-blocking)
        saved_memories = []
        try:
            saved_memories = self.mem_mgr.extract_and_save_memories(
                user_message=user_message,
                assistant_response=response_text,
            )
        except Exception as e:
            logger.warning(f"Background memory extraction failed: {e}")

        # 8. Store assistant response in database
        metadata = {}
        if tool_calls:
            metadata["tool_calls"] = [t.model_dump() for t in tool_calls]
        if saved_memories:
            metadata["saved_memories"] = [m.model_dump() for m in saved_memories]

        self.conv_mgr.add_message(
            db=db,
            conversation_id=conv_id,
            role="assistant",
            content=response_text,
            metadata=metadata if metadata else None,
        )

        # 9. Return structured ChatResponse
        return ChatResponse(
            response=response_text,
            conversation_id=conv_id,
            tool_calls=tool_calls,
            saved_memories=saved_memories,
        )


# Global singleton orchestrator
jarvis_orchestrator = JarvisOrchestrator()
