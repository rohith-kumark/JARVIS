import os
import sys
from pathlib import Path
import pytest

# Add project root to sys.path so 'backend' package is always resolvable
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Force test environment variables before application import
os.environ["DEFAULT_LLM_PROVIDER"] = "mock"
os.environ["APP_ENV"] = "test"

from backend.app.main import app
from backend.app.llm.mock import MockLLMClient
from backend.app.services.orchestrator import AgentOrchestrator
from backend.app.tools.registry import registry


@pytest.fixture(autouse=True)
def configure_test_state():
    """Ensure test suite runs deterministically with MockLLMClient."""
    mock_llm = MockLLMClient()
    app.state.llm_client = mock_llm
    app.state.llm_provider_name = "mock"
    app.state.orchestrator = AgentOrchestrator(llm_client=mock_llm, tool_registry=registry)
    yield
