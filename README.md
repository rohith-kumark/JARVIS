# J.A.R.V.I.S. — Personal AI Assistant (Phase 1)

JARVIS (Just A Rather Very Intelligent System) is a modular personal AI assistant engineered with a high-performance Python FastAPI backend, Google Gemini LLM reasoning engine, dynamic Python tool execution, short-term SQLite memory, and a React + Vite sci-fi HUD frontend.

---

## Architecture

The system follows a strict, controlled execution pipeline:

```
React Frontend
      ↓ (REST HTTP)
FastAPI Backend
      ↓
JARVIS Orchestrator
      ↓
Gemini LLM (google-genai)
      ↓ (Function Calling)
Tool Manager
      ↓
Individual Python Tools (calculator, get_current_time)
      ↓
SQLite Database (conversations, messages, memories, preferences, tool_executions)
```

### Purpose of Major Modules

| Directory / Module | Purpose |
| :--- | :--- |
| `backend/app/main.py` | FastAPI application initialization, CORS middleware, lifespan startup/shutdown hooks, and centralized error handling. |
| `backend/app/core/config.py` | Pydantic `BaseSettings` that validates and loads configuration from `.env`. |
| `backend/app/core/logging.py` | Centralized structured logging configuration. |
| `backend/app/core/exceptions.py` | Custom domain exceptions (`ToolSecurityError`, `LLMServiceError`, `ConversationNotFoundError`). |
| `backend/app/db/models.py` | SQLAlchemy ORM models for `Conversation`, `Message`, `Memory`, `UserPreference`, and `ToolExecution`. |
| `backend/app/db/session.py` | Database engine and sessionmaker abstraction. Modular design allows seamless replacement of SQLite with PostgreSQL. |
| `backend/app/tools/base.py` | Protocol and `BaseTool` abstract base class defining standard tool interface (`name`, `description`, `parameters`, `execute()`). |
| `backend/app/tools/registry.py` | Dynamic `ToolRegistry` allowing runtime tool discovery, registration, and conversion into Gemini function declarations. |
| `backend/app/tools/manager.py` | `ToolManager` providing execution containment, safety boundaries, latency timing, and database auditing. |
| `backend/app/tools/builtin/calculator.py` | Safe AST-based mathematical evaluator. **Never** executes arbitrary Python or OS code; only permits safe arithmetic AST nodes. |
| `backend/app/tools/builtin/current_time.py` | Safe system time and date lookup tool. |
| `backend/app/memory/conversation_manager.py` | Handles conversation session creation, message persistence, and chronological history retrieval. |
| `backend/app/memory/memory_manager.py` | Manages short-term contextual memories and user preferences, formatting context injection for the LLM prompt. |
| `backend/app/llm/gemini_service.py` | Wrapper for official `google-genai` SDK. Binds registered tools, creates multi-turn chats, handles function calling loops, and features mock fallback for offline operation. |
| `backend/app/orchestrator/orchestrator.py` | Central conductor coordinating memory retrieval, conversation loading, Gemini reasoning, tool execution, and response storage. |
| `backend/app/api/routes/` | REST endpoints: `/api/chat`, `/api/health`, `/api/conversations`, `/api/memory`. |
| `frontend/src/` | React + Vite client featuring dark cyan HUD interface, message streaming, tool call execution badges, and memory inspection. |

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup

```bash
# Navigate to project root
cd /home/rk/Documents/Jarvis

# Create virtual environment if not already created
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and configure your Google Gemini API key:

```bash
cp backend/.env.example .env
```

Open `.env` and provide your settings:

```dotenv
APP_NAME="JARVIS AI Assistant"
APP_ENV="development"
DEBUG=true

HOST="0.0.0.0"
PORT=8000

CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
DATABASE_URL="sqlite:///./jarvis.db"

# Google Gemini API Configuration (from https://aistudio.google.com/)
GEMINI_API_KEY="your_gemini_api_key_here"
GEMINI_MODEL="gemini-3.6-flash"
DEFAULT_LLM_PROVIDER="gemini"

LOG_LEVEL="INFO"
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

### Start the Backend (FastAPI)

```bash
source .venv/bin/activate
python backend/run.py
```
*Backend runs on `http://127.0.0.1:8000` (API docs available at `http://127.0.0.1:8000/docs`).*

### Start the Frontend (React + Vite)

```bash
cd frontend
npm run dev
```
*Frontend runs on `http://localhost:5173`.*

---

## Testing

Run the automated test suite using `pytest`:

```bash
source .venv/bin/activate
pytest -v
```

The test suite covers:
- Safe AST calculator evaluation & security containment (blocking `eval`, `__import__`, variables, attributes).
- Current time formatting.
- SQLite ORM models and cascaded deletes.
- Dynamic tool registration and manager execution.
- Complete chat orchestration, conversation history, and memory inspection.
- Health-check endpoint diagnostics.

---

## API Endpoints

### 1. `POST /api/chat`
Process user message through JARVIS Orchestrator.
- **Request**:
  ```json
  {
    "message": "What is 45 * 12?",
    "conversation_id": null
  }
  ```
- **Response**:
  ```json
  {
    "response": "45 * 12 = 540",
    "conversation_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "tool_calls": [
      {
        "tool_name": "calculator",
        "arguments": { "expression": "45 * 12" },
        "result": { "result": 540 },
        "status": "success",
        "execution_time_ms": 0.42
      }
    ],
    "created_at": "2026-09-24T21:00:00Z"
  }
  ```

### 2. `GET /api/health`
System diagnostics and status report.
- **Response**:
  ```json
  {
    "status": "ok",
    "app_name": "JARVIS AI Assistant",
    "version": "1.0.0",
    "environment": "development",
    "database": "connected",
    "llm_provider": "gemini",
    "model": "gemini-3.6-flash",
    "tools_count": 2,
    "registered_tools": ["get_current_time", "calculator"]
  }
  ```

### 3. `GET /api/conversations`
List all conversation sessions.

### 4. `POST /api/conversations`
Create a new conversation session.

### 5. `GET /api/conversations/{id}`
Retrieve complete message history for a conversation.

### 6. `GET /api/memory`
Retrieve short-term contextual memories and user preferences.

---

## Security Safeguards

- **No Arbitrary Python Execution**: The calculator tool parses input into an Abstract Syntax Tree (AST) and evaluates only strictly whitelisted numerical constants and binary operators. Any attempt to use identifiers, imports, calls, attributes, or functions is blocked with `ToolSecurityError`.
- **API Key Secrecy**: The Gemini API key is loaded only on the FastAPI backend from `.env` and is never transmitted or exposed to the client.
- **Strict Input Validation**: All endpoints validate request structures and data limits with Pydantic.
- **Safe Isolation**: Operating-system shell commands and arbitrary execution capabilities are completely omitted in Phase 1.
