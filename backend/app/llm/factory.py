import logging
from typing import Optional
from backend.app.core.config import Settings, get_settings
from backend.app.llm.base import BaseLLMClient
from backend.app.llm.gemini import GeminiLLMClient
from backend.app.llm.mock import MockLLMClient

logger = logging.getLogger(__name__)


def create_llm_client(settings: Optional[Settings] = None) -> BaseLLMClient:
    """
    Factory function to instantiate the configured LLM provider.
    Automatically falls back to MockLLMClient if no GEMINI_API_KEY is configured.
    """
    app_settings = settings or get_settings()

    provider = app_settings.DEFAULT_LLM_PROVIDER.lower()

    if provider == "gemini":
        if app_settings.GEMINI_API_KEY:
            logger.info(f"Initializing Gemini LLM client (model: {app_settings.GEMINI_MODEL})")
            return GeminiLLMClient(
                api_key=app_settings.GEMINI_API_KEY,
                model=app_settings.GEMINI_MODEL
            )
        else:
            logger.warning(
                "GEMINI_API_KEY is not set. Falling back to MockLLMClient for offline development/testing. "
                "Set GEMINI_API_KEY in backend/.env to connect to Google Gemini."
            )
            return MockLLMClient()

    elif provider == "mock":
        logger.info("Initializing MockLLMClient as configured")
        return MockLLMClient()

    else:
        logger.warning(f"Unknown LLM provider '{provider}'. Defaulting to MockLLMClient.")
        return MockLLMClient()
