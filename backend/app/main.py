"""Main FastAPI application entry point for JARVIS AI assistant."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import chat_router, conversations_router, health_router, memory_router
from backend.app.core.config import get_settings
from backend.app.core.exceptions import JarvisBaseException
from backend.app.core.logging import setup_logging
from backend.app.db.session import init_db
from backend.app.tools.registry import tool_registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager handling application startup and shutdown events."""
    settings = get_settings()

    # 1. Setup logging
    setup_logging(level=settings.LOG_LEVEL)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # 2. Initialize database schema
    init_db()

    # 3. Register default safe demonstration tools
    tool_registry.register_builtins()
    logger.info(f"Loaded {len(tool_registry.list_tools())} tools into registry: {tool_registry.list_names()}")

    yield

    logger.info("Shutting down JARVIS AI Assistant backend...")


def create_app() -> FastAPI:
    """Application factory for FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="JARVIS Personal AI Assistant - Phase 1 Core Reasoning and Tool Execution Engine",
        lifespan=lifespan,
    )

    # Configure CORS for React frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Domain exception handler
    @app.exception_handler(JarvisBaseException)
    async def jarvis_exception_handler(request: Request, exc: JarvisBaseException):
        logger.error(f"Domain exception: {exc.message}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.message,
                "type": exc.__class__.__name__,
                "details": exc.details,
            },
        )

    # Global unhandled exception handler
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

    # Register API routers
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(conversations_router)
    app.include_router(memory_router)

    return app


app = create_app()
