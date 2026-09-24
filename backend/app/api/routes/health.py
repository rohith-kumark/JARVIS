import time
from fastapi import APIRouter, Request
from backend.app.core.config import get_settings
from backend.app.schemas.health import HealthCheckResponse
from backend.app.tools.registry import registry

router = APIRouter(prefix="/api/health", tags=["Health"])

START_TIME = time.time()


@router.get("", response_model=HealthCheckResponse)
async def get_health(request: Request) -> HealthCheckResponse:
    """
    System health check endpoint.
    Returns status, environment, active LLM provider, registered tools count, and uptime.
    """
    settings = get_settings()
    llm_provider = getattr(request.app.state, "llm_provider_name", "unknown")
    uptime = round(time.time() - START_TIME, 2)

    return HealthCheckResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        llm_provider=llm_provider,
        tools_registered_count=len(registry.list_tools()),
        uptime_seconds=uptime,
    )
