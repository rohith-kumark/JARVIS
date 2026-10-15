# J.A.R.V.I.S. — Personal AI Assistant

JARVIS (**Just A Rather Very Intelligent System**) is a modular, production-grade personal AI assistant engineered with a high-performance Python FastAPI backend, Google Gemini LLM reasoning engine, dynamic tool execution, persistent long-term memory, real-time bidirectional voice streaming via Gemini Live API, and a futuristic sci-fi React HUD frontend.

---

## Evolution Roadmap

JARVIS is built incrementally with modular layers, where each phase is tested and hardened before advancing:

* **Phase 1: Foundation Architecture** — FastAPI backend, Gemini multi-turn orchestration, AST-sandboxed safe tool framework, SQLite storage, and React HUD chat interface.
* **Phase 2: Persistent Long-Term Memory** — JSON-backed long-term store, automatic background extraction, hybrid keyword/tokenization retriever, and HUD memory inspector modal.
* **Phase 3: Real-Time Voice Assistant** — Full-duplex Gemini Live API integration, 16kHz/24kHz streaming PCM audio, real-time barge-in interruption handling, and reactive holographic Voice HUD.

---

## Architecture Pipeline

```
                     ┌─────────────────────────────────────────────────────────┐
                     │              React + Vite HUD Frontend                  │
                     │  - Holographic Chat Interface  - Holographic Voice HUD  │
                     │  - Interactive Memory Manager  - Real-Time Visualizer   │
                     └───────────────▲─────────────────────────▲───────────────┘
                                     │                         │
                               (REST / JSON)             (WebSocket PCM)
                                     │                         │
                     ┌───────────────▼─────────────────────────▼───────────────┐
                     │               FastAPI Backend Gateway                   │
                     │  - CORS / Lifespan Hooks      - Structured Logging      │
                     │  - Security & Pydantic Validation - Custom Exceptions   │
                     └───────┬─────────────────────────────────────────┬───────┘
                             │                                         │
                   [Chat / Memory Route]                         [Voice Route]
                             │                                         │
            ┌────────────────▼───────────────┐        ┌────────────────▼───────────────┐
            │       JARVIS Orchestrator      │        │      Voice Session Manager     │
            │  - Multi-Turn Conversation     │        │  - Bidirectional Stream Sync   │
            │  - Dynamic Context Builder     │        │  - State Machine & Transitions │
            │  - Multi-Model Failover        │        │  - Real-Time Barge-In / Ducking│
            └───────┬──────────────┬─────────┘        └────────────────┬───────────────┘
                    │              │                                   │
        ┌───────────▼──┐   ┌───────▼──────────┐                        │
        │ Memory Engine│   │   Tool Manager   │                        │
        │ - Extractor  │   │ - Safe AST Calc  │                        │
        │ - Retriever  │   │ - Time & System  │                        │
        │ - JSON Store │   │ - Execution Audit│                        │
        └───────────┬──┘   └───────┬──────────┘                        │
                    │              │                                   │
                    ▼              ▼                                   ▼
          ┌───────────────────────────────────┐       ┌────────────────────────────────┐
          │     Google Gemini API Engine      │       │     Gemini Live API Client     │
          │ (gemini-3.6-flash / 3-flash-prev) │       │ (Bidirectional PCM Audio Live) │
          └───────────────────────────────────┘       └────────────────────────────────┘
```

---

## Phase Implementations

### Phase 1 — Core Foundation & Tool Orchestration
* **FastAPI Backend Architecture**: Lifespan startup/shutdown management, CORS middleware, centralized structured logging, and robust domain exception handling (`ToolSecurityError`, `LLMServiceError`, `ConversationNotFoundError`).
* **Safe Tool Calling Pipeline**: `ToolRegistry` and `ToolManager` enabling runtime tool discovery, conversion to Gemini function schemas, latency tracking, and audit logging.
* **AST-Sandboxed Tools**:
  * `calculator`: Strict Python AST parsing allowing only whitelisted numerical constants and binary operations; blocks any arbitrary code execution, `eval`, `exec`, attribute access, or system imports.
  * `get_current_time`: Safe timezone-aware system date and time resolver.
* **SQLite Persistence**: SQLAlchemy ORM models managing `Conversation`, `Message`, `Memory`, `UserPreference`, and `ToolExecution`.
* **Sci-Fi HUD Frontend**: React + Vite interface with holographic cyan design, streaming message displays, tool execution cards, and live system health monitors.

### Phase 2 — Persistent Long-Term Memory System
* **Long-Term Memory Store (`store.py`)**: Persistent JSON storage backing structured memory entities (`MemoryRecord`) with automatic thread-safe file handling and corruption recovery.
* **Automatic Silent Extraction (`extractor.py`)**: Asynchronous background analyzer scanning chat interactions for personal preferences, routines, project details, and factual rules, retaining information silently without annoying chat confirmations.
* **Dynamic Memory Retriever (`retriever.py`)**: Tokenization, Jaccard similarity scoring, and category importance weighting to retrieve relevant contextual memories and inject them dynamically into the Gemini system prompt.
* **HUD Memory Inspector (`MemoryModal.jsx`)**: Comprehensive holographic modal enabling users to search, filter by category (`personal_preference`, `routine`, `project`, `factual_rule`), create, edit, and delete memories.
* **Resilient Multi-Model Failover**: Intelligent cascading failover across `gemini-3.6-flash`, `gemini-3-flash-preview`, and `gemini-3.5-flash-lite` with standby fallback when API rate limits occur.

### Phase 3 — Real-Time Voice Assistant (Gemini Live API)
* **Bidirectional Live Audio Streaming**: Full-duplex voice connection to Gemini Multimodal Live API via WebSockets.
* **Dual Audio Pipelines**:
  * **Input (Mic)**: Captures 16kHz 16-bit mono linear PCM audio via browser `AudioWorklet` / `ScriptProcessor` and streams base64 chunks to backend.
  * **Output (Speaker)**: Receives synthesized 24kHz PCM audio chunks from Gemini Live, queued and scheduled seamlessly with the Web Audio API.
* **Real-Time Barge-In & Interruption**: Instant cancellation of active model audio playback upon user speech detection. The frontend purges its playback buffer while the backend sends an interrupt signal to the Gemini Live session.
* **Voice Session State Machine**: Robust session lifecycle managing transitions across `IDLE`, `CONNECTING`, `LISTENING`, `THINKING`, `SPEAKING`, `INTERRUPTED`, and `ERROR`.
* **Holographic Voice HUD (`VoiceHUD.jsx`)**: Floating reactive widget featuring pulsating multi-ring animations, dynamic audio waveform visualization, live status indicators, microphone muting, and session toggling.

---

## Directory & Module Structure

| Directory / File | Phase | Description |
| :--- | :--- | :--- |
| `backend/app/main.py` | 1 | FastAPI app initialization, middleware, lifecycle handlers, and routing. |
| `backend/app/core/config.py` | 1-3 | Pydantic application settings (API keys, models, audio rates, database). |
| `backend/app/core/prompt_provider.py`| 3 | Centralized system instructions and persona definitions for chat & voice. |
| `backend/app/core/exceptions.py` | 1 | Custom domain exception classes for security and execution containment. |
| `backend/app/db/models.py` | 1 | SQLAlchemy database models for conversations, messages, and tool audits. |
| `backend/app/db/session.py` | 1 | Database session manager and engine abstraction. |
| `backend/app/tools/registry.py` | 1 | Tool discovery and Gemini function declaration generation. |
| `backend/app/tools/manager.py` | 1 | Tool execution supervisor with sandboxing and execution latency measurement. |
| `backend/app/tools/builtin/calculator.py` | 1 | Safe AST mathematical evaluator. |
| `backend/app/tools/builtin/current_time.py` | 1 | System time and timezone lookup tool. |
| `backend/app/llm/gemini_service.py` | 1-2 | Multi-turn chat orchestration with function calling and multi-model failover. |
| `backend/app/memory/store.py` | 2 | Persistent JSON-based long-term memory storage engine. |
| `backend/app/memory/extractor.py` | 2 | Background entity and fact extractor from conversation turns. |
| `backend/app/memory/retriever.py` | 2 | Keyword tokenization and similarity-based memory ranking engine. |
| `backend/app/voice/audio.py` | 3 | Audio format conversion, validation, PCM resampling, and queue management. |
| `backend/app/voice/live_client.py` | 3 | Asynchronous client interfacing with Gemini Multimodal Live API. |
| `backend/app/voice/session.py` | 3 | Bidirectional voice session coordinator with barge-in support. |
| `backend/app/voice/manager.py` | 3 | Active voice session registry and connection tracker. |
| `backend/app/api/routes/chat.py` | 1 | REST endpoint for conversational text interaction. |
| `backend/app/api/routes/memory.py` | 2 | REST endpoints for managing and inspecting long-term memory. |
| `backend/app/api/routes/voice.py` | 3 | WebSocket and REST endpoints for voice streaming and session controls. |
| `frontend/src/components/VoiceHUD.jsx` | 3 | Holographic floating voice controller with waveform visualizer. |
| `frontend/src/components/MemoryModal.jsx` | 2 | Interactive modal for searching, editing, and managing memories. |
| `frontend/src/services/audioStreamer.js` | 3 | Web Audio API streamer handling 16kHz PCM capture and 24kHz playback. |

---

## Installation & Setup

### Prerequisites
* Python 3.10+
* Node.js 18+ and npm
* Microphone & Audio Output (for Phase 3 Voice interaction)

### 1. Backend Setup

```bash
# Navigate to repository root
cd /home/rk/Documents/Jarvis

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (FastAPI, google-genai, sounddevice, numpy, etc.)
pip install -r backend/requirements.txt
```

### 2. Environment Configuration

Copy the example configuration file:
```bash
cp backend/.env.example .env
```

Edit `.env` and supply your Gemini API key:
```dotenv
# Application Settings
APP_NAME="JARVIS AI Assistant"
APP_ENV="development"
DEBUG=true

# Server Network Settings
HOST="0.0.0.0"
PORT=8000
CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

# Database URL
DATABASE_URL="sqlite:///./jarvis.db"

# LLM Reasoning Engine Configuration (https://aistudio.google.com/)
GEMINI_API_KEY="your-gemini-api-key-here"
GEMINI_MODEL="gemini-3.6-flash"
DEFAULT_LLM_PROVIDER="gemini"

# Phase 3 Voice Configuration
VOICE_ENABLED=true
GEMINI_LIVE_MODEL="gemini-2.0-flash-exp"
VOICE_SAMPLE_RATE_INPUT=16000
VOICE_SAMPLE_RATE_OUTPUT=24000
VOICE_CHANNELS=1

# Observability
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
*Backend server runs on `http://127.0.0.1:8000` (interactive API documentation available at `http://127.0.0.1:8000/docs`).*

### Start the Frontend (React + Vite HUD)
```bash
cd frontend
npm run dev
```
*Frontend runs on `http://localhost:5173`.*

---

## API & WebSocket Reference

### 1. Chat & Orchestration (Phase 1)
* `POST /api/chat` — Process conversation turn through JARVIS Orchestrator with memory retrieval and tool calling.
* `GET /api/conversations` — Retrieve list of active and past conversation threads.
* `GET /api/conversations/{id}` — Fetch chronological message history.
* `GET /api/health` — Complete backend diagnostics (database, LLM engine, tools registered).

### 2. Long-Term Memory (Phase 2)
* `GET /api/memory` — Retrieve short-term contextual memories and user preferences.
* `GET /api/memory/long-term` — Search or list all long-term memories with optional category filtering.
* `POST /api/memory/long-term` — Manually create a new structured long-term memory.
* `PUT /api/memory/long-term/{id}` — Update an existing memory's content or importance score.
* `DELETE /api/memory/long-term/{id}` — Remove a memory from persistent storage.

### 3. Real-Time Voice Streaming (Phase 3)
* `WebSocket /api/voice/ws` — Bidirectional full-duplex PCM audio stream and real-time control protocol.
* `GET /api/voice/session/status` — Current status of voice engine, active connections, and latency metrics.
* `GET /api/voice/voices` — Available Gemini Live voice personas (`Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`).
* `GET /api/voice/devices` — Enumerate host audio input/output hardware devices.
* `POST /api/voice/session/stop` — Explicitly terminate an active live audio session.

---

## Automated Testing

JARVIS includes a comprehensive automated test suite built with `pytest` covering all Phase 1, Phase 2, and Phase 3 capabilities:

```bash
source .venv/bin/activate
pytest -v
```

### Test Coverage Highlights
* **Tools & AST Sandbox (`test_calculator.py`, `test_tools.py`)**: Evaluates math operations, division by zero, DoS exponentiation limits, and ensures arbitrary code execution attempts (`__import__`, `eval`, system commands) are safely rejected.
* **Database & Persistence (`test_database.py`)**: Verifies SQLite ORM models, session lifecycles, and cascaded message deletions.
* **Long-Term Memory Suite (`test_memory.py`)**: 18 comprehensive tests verifying CRUD operations, automatic extraction, Jaccard similarity scoring, duplicate detection, corrupted JSON recovery, and prompt injection.
* **Real-Time Voice Suite (`test_voice.py`)**: 16 dedicated tests covering audio PCM validation, base64 roundtrips, audio resampling, queue isolation, voice session state transitions, barge-in interruption logic, and WebSocket communication protocols.

---

## Security Safeguards

1. **AST Execution Containment**: The calculator executes solely through Python's `ast` module against a strict whitelist of arithmetic operations. No arbitrary code execution is permitted.
2. **Zero Client Secret Exposure**: API keys are isolated exclusively within backend environment variables; client applications never access Gemini or database credentials directly.
3. **Safe Audio Buffering**: Voice audio streams are bounded with memory queue limits and strict PCM byte validation to prevent buffer exhaustion.
4. **Resilient Error Recovery**: Corrupted memory files are automatically restored from backup defaults without crashing the service, and Gemini rate limits seamlessly fall back to secondary models.
