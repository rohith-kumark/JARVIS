"""VoiceManager coordinator managing active voice sessions."""

import asyncio
import logging
from typing import Dict, List, Optional

from backend.app.voice.config import VoiceConfig
from backend.app.voice.session import VoiceSession

logger = logging.getLogger(__name__)


class VoiceManager:
    """Manages active voice sessions across WebSocket and local hardware streams."""

    def __init__(self) -> None:
        self._sessions: Dict[str, VoiceSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        session_id: Optional[str] = None,
        config: Optional[VoiceConfig] = None,
    ) -> VoiceSession:
        """Create and track a new voice session."""
        async with self._lock:
            session = VoiceSession(session_id=session_id, config=config)
            self._sessions[session.session_id] = session
            logger.info(f"Registered voice session [{session.session_id}]. Active: {len(self._sessions)}")
            return session

    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Retrieve an active voice session by ID."""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        """Close and remove a specific voice session."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                await session.cleanup()
                logger.info(f"Closed voice session [{session_id}]. Remaining: {len(self._sessions)}")

    async def close_all(self) -> None:
        """Cleanly close all active voice sessions (invoked on server shutdown)."""
        async with self._lock:
            session_ids = list(self._sessions.keys())
            for sid in session_ids:
                session = self._sessions.pop(sid, None)
                if session:
                    try:
                        await session.cleanup()
                    except Exception as e:
                        logger.warning(f"Error cleaning up session [{sid}]: {e}")
            logger.info("All active voice sessions cleaned up.")

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)


# Global singleton voice manager
voice_manager = VoiceManager()
