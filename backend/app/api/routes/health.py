"""Health check and diagnostics API router."""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.llm.gemini_service import gemini_service
from backend.app.schemas.health import HealthResponse
from backend.app.tools.registry import tool_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Return health status of the JARVIS backend, database, and tool registry."""
    settings = get_settings()

    # Check database status
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"unhealthy: {str(e)}"

    # Check LLM provider
    provider = "gemini" if gemini_service.is_configured else "mock"
    if settings.DEFAULT_LLM_PROVIDER.lower() == "mock":
        provider = "mock (configured)"

    tools = tool_registry.list_names()

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        database=db_status,
        llm_provider=provider,
        model=settings.GEMINI_MODEL,
        tools_count=len(tools),
        registered_tools=tools,
    )
