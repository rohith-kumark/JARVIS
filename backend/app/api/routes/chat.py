import logging
from fastapi import APIRouter, HTTPException, Request
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, req: Request) -> ChatResponse:
    """REST endpoint for sending a message to JARVIS."""
    orchestrator: AgentOrchestrator = req.app.state.orchestrator
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Agent orchestrator not initialized")

    try:
        response = await orchestrator.run_loop(
            user_message=request.message,
            session_id=request.session_id,
            caller_permission=request.caller_permission,
        )
        return response
    except Exception as exc:
        logger.error(f"Error in chat processing: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
