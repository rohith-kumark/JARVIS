# J.A.R.V.I.S. (Modular AI Personal Assistant)

> **Core Philosophy**: Gemini is the reasoning/decision-making layer. Python is the execution layer. Every external action happens exclusively through a controlled tool.

---

## 🏛 System Architecture Overview

```
                                  +------------------------------------+
                                  |         React + Vite (UI)          |
                                  |  - Presentation Components         |
                                  |  - Custom React Hooks              |
                                  |  - Isolated Agent Service Layer    |
                                  +-----------------+------------------+
                                                    |
                                     WebSocket /    |  REST
                                     HTTP           v
+---------------------------------------------------+---------------------------------------------------+
| BACKEND CORE (FastAPI)                                                                                |
|                                                                                                       |
|  +--------------------------+          +-------------------------+          +----------------------+  |
|  |       API Routers        | -------> |    Agent Orchestrator   | -------> |    LLM Abstraction   |  |
|  | - /api/health            |          |  (Reasoning & Loop)     |          |  - BaseLLMClient     |  |
|  | - /api/tools             |          +------------+------------+          |  - GeminiLLMClient   |  |
|  | - /api/chat              |                       |                       |  - MockLLMClient     |  |
|  | - /api/ws                |                       |                       +----------------------+  |
|  +--------------------------+                       v                                                 |
|                                        +-------------------------+                                    |
|                                        |  Central Tool Registry  |                                    |
|                                        |  - Permission Clearance |                                    |
|                                        |  - Schema Validation    |                                    |
|                                        |  - Auto-Discovery       |                                    |
|                                        +------------+------------+                                    |
|                                                     |                                                 |
|                                                     v                                                 |
|                                        +-------------------------+                                    |
|                                        |     Controlled Tools    |                                    |
|                                        |  - get_system_info      |                                    |
|                                        |  - [Future Tools...]    |                                    |
|                                        +-------------------------+                                    |
+-------------------------------------------------------------------------------------------------------+
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup

```bash
# Navigate to workspace root
cd /home/rk/Documents/Jarvis

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env and optionally add your GEMINI_API_KEY
```

> **Note on Offline Development**: If `GEMINI_API_KEY` is omitted, JARVIS automatically boots in `MockLLMClient` mode, providing full offline testing and simulation of reasoning and tool calls!

To run the backend server:
```bash
python backend/run.py
# Server starts at http://localhost:8000
# API docs available at http://localhost:8000/docs
```

To run the automated backend test suite:
```bash
pytest -v backend/tests
```

---

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env

# Run Vite development server
npm run dev
# Interface opens at http://localhost:5173
```

---

## 🛠 Adding New Tools Without Modifying the Core Orchestrator

The system uses an auto-discovering tool registry. To add a new tool:

1. Create a new Python file in `backend/app/tools/builtin/`, e.g., `web_search.py`.
2. Inherit from `BaseTool` and decorate with `@register_tool`:

```python
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, PermissionLevel
from backend.app.tools.registry import register_tool

class SearchArgs(BaseModel):
    query: str = Field(description="The search query string")

@register_tool
class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Searches the web for given keywords and returns top summaries"
    permission_level = PermissionLevel.READ_ONLY
    args_schema = SearchArgs

    async def _run(self, query: str):
        # Implementation logic goes here
        return {"query": query, "results": ["Summary 1", "Summary 2"]}
```

3. **That's it!** Upon startup, `registry.discover_builtin_tools()` dynamically loads your tool, generates its JSON Schema, advertises it to the LLM, and enforces permissions automatically.

---

## 🔒 Security Clearance Levels

Every tool declares a minimum permission rank:
- `READ_ONLY`: Passive inspection (e.g., system diagnostics, memory queries).
- `EXECUTE`: Standard external actions (e.g., calculations, opening local apps).
- `SENSITIVE`: Actions modifying external state (e.g., sending emails, writing files).
- `ADMIN`: Full authority (e.g., process termination, credential management, system settings).
