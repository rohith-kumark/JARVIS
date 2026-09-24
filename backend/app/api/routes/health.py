import time
from fastapi import APIRouter, Request
from backend.app.core.config import get_settings
from backend.app.db.session import check_db_health
from backend.app.db.vector_store import get_vector_store
from backend.app.schemas.health import HealthCheckResponse
from backend.app.tools.registry import registry

router = APIRouter(prefix="/api/health", tags=["Health"])

START_TIME = time.time()


@router.get("", response_model=HealthCheckResponse)
async def get_health(request: Request) -> HealthCheckResponse:
    """
    System health check endpoint.
    Returns status, environment, active LLM provider, registered tools count,
    PostgreSQL connectivity status, and Vector Store status.
    """
    settings = get_settings()
    llm_provider = getattr(request.app.state, "llm_provider_name", "unknown")
    uptime = round(time.time() - START_TIME, 2)

    # Probe Database and Vector Store asynchronously
    db_health = await check_db_health()
    vector_store = get_vector_store()
    vector_health = await vector_store.health_check()

    return HealthCheckResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        llm_provider=llm_provider,
        tools_registered_count=len(registry.list_tools()),
        database_status=db_health.get("status", "unknown"),
        vector_store_status=vector_health.get("status", "unknown"),
        vector_documents_count=vector_health.get("vector_count", 0),
        uptime_seconds=uptime,
    )
