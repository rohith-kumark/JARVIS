import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import chat, health, tools, ws
from backend.app.core.config import get_settings
from backend.app.core.exceptions import JarvisBaseException
from backend.app.core.logging import setup_logging
from backend.app.llm.factory import create_llm_client
from backend.app.services.orchestrator import AgentOrchestrator
from backend.app.tools.registry import registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown hooks."""
    settings = get_settings()

    # 1. Initialize logging
    setup_logging(level=settings.LOG_LEVEL, structured=(settings.APP_ENV == "production"))
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # 2. Auto-discover registered builtin tools
    registry.discover_builtin_tools()
    logger.info(f"Loaded {len(registry.list_tools())} tools into central registry")

    # 3. Initialize LLM abstraction
    llm_client = create_llm_client(settings)
    app.state.llm_client = llm_client
    app.state.llm_provider_name = llm_client.provider_name

    # 4. Initialize Agent Orchestrator service
    orchestrator = AgentOrchestrator(llm_client=llm_client, tool_registry=registry)
    app.state.orchestrator = orchestrator
    logger.info(f"Agent Orchestrator initialized with provider: {llm_client.provider_name}")

    yield

    logger.info("Shutting down JARVIS Core services...")


def create_application() -> FastAPI:
    """FastAPI application factory."""
    settings = get_settings()

    # Pre-discover tools and initialize baseline state
    registry.discover_builtin_tools()
    initial_llm = create_llm_client(settings)
    initial_orchestrator = AgentOrchestrator(llm_client=initial_llm, tool_registry=registry)

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Modular Personal AI Assistant - Core Reasoning and Controlled Execution Engine",
        lifespan=lifespan,
    )

    app.state.llm_client = initial_llm
    app.state.llm_provider_name = initial_llm.provider_name
    app.state.orchestrator = initial_orchestrator

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handlers
    @app.exception_handler(JarvisBaseException)
    async def jarvis_exception_handler(request: Request, exc: JarvisBaseException):
        logger.error(f"Jarvis domain exception: {exc.message}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.message,
                "type": exc.__class__.__name__,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "An internal server error occurred",
                "details": str(exc) if settings.DEBUG else None,
            },
        )

    # Include API Routers
    app.include_router(health.router)
    app.include_router(tools.router)
    app.include_router(chat.router)
    app.include_router(ws.router)

    return app


app = create_application()
