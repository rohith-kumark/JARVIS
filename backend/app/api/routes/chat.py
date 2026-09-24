"""Chat API router."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.exceptions import JarvisBaseException
from backend.app.db.session import get_db
from backend.app.orchestrator.orchestrator import jarvis_orchestrator
from backend.app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Execute a conversational reasoning turn through the JARVIS Orchestrator."""
    try:
        return jarvis_orchestrator.process_message(
            user_message=request.message,
            conversation_id=request.conversation_id,
            db=db,
        )
    except JarvisBaseException as e:
        logger.error(f"Domain error processing chat message: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}",
        )
