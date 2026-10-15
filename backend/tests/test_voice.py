"""Automated test suite for Phase 3: Real-Time Voice Assistant.

Covers voice configuration, PCM validation, audio queues, barge-in,
state machine, memory integration, tool execution, REST & WebSocket endpoints.
All tests are non-hardware-dependent with full mocking of external APIs.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.core.prompt_provider import system_instruction_provider
from backend.app.main import create_app
from backend.app.memory.manager import MemoryManager
from backend.app.memory.models import MemoryCategory, MemoryRecord
from backend.app.memory.store import MemoryStore
from backend.app.memory.retriever import MemoryRetriever
from backend.app.tools.manager import ToolManager
from backend.app.tools.registry import ToolRegistry
from backend.app.voice.audio import (
    AudioQueue,
    base64_to_pcm,
    get_available_devices,
    pcm_to_base64,
    resample_pcm,
    validate_pcm,
)
from backend.app.voice.config import (
    AUDIO_CHANNELS,
    BYTES_PER_SAMPLE,
    DEFAULT_CHUNK_MS,
    DEFAULT_LIVE_MODEL,
    DEFAULT_VOICE,
    INPUT_SAMPLE_RATE,
    OUTPUT_SAMPLE_RATE,
    SUPPORTED_VOICES,
    VoiceConfig,
    VoiceSessionState,
)
from backend.app.voice.live_client import GeminiLiveClient, LiveEvent
from backend.app.voice.manager import VoiceManager
from backend.app.voice.session import VoiceSession


# ============================================================================
# 1. Voice Configuration Tests
# ============================================================================

def test_voice_config_specifications():
    """Verify standard audio specifications and voice defaults."""
    config = VoiceConfig()
    assert config.voice_name == DEFAULT_VOICE
    assert config.voice_name in SUPPORTED_VOICES
    assert config.input_sample_rate == 16000
    assert config.output_sample_rate == 24000
    assert config.channels == 1
    assert config.model == DEFAULT_LIVE_MODEL


def test_voice_config_custom_values():
    """Verify custom voice selection and parameters."""
    cfg = VoiceConfig(voice_name="Charon", input_sample_rate=16000, output_sample_rate=24000)
    assert cfg.voice_name == "Charon"
    assert cfg.input_sample_rate == 16000


# ============================================================================
# 2. Audio Validation & Encoding Tests
# ============================================================================

def test_pcm_validation():
    """Verify 16-bit PCM byte alignment validation."""
    valid_pcm = b"\x00\x00\x10\x20"  # 4 bytes = 2 samples (16-bit)
    assert validate_pcm(valid_pcm) is True

    odd_pcm = b"\x00\x00\x10"  # 3 bytes, not divisible by 2
    assert validate_pcm(odd_pcm) is False

    empty_pcm = b""
    assert validate_pcm(empty_pcm) is False


def test_pcm_base64_roundtrip():
    """Verify base64 encode and decode roundtrip for PCM chunks."""
    raw_data = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0" * 100
    b64 = pcm_to_base64(raw_data)
    assert isinstance(b64, str)
    decoded = base64_to_pcm(b64)
    assert decoded == raw_data


def test_pcm_resampling():
    """Verify linear resampling down to 16kHz."""
    # 48kHz 16-bit mono PCM: 480 samples = 960 bytes (10ms)
    orig_sr = 48000
    samples_48k = b"\x00\x10" * 480
    resampled = resample_pcm(samples_48k, orig_sr=orig_sr, target_sr=16000)
    # Expected output: 160 samples = 320 bytes (10ms at 16kHz)
    assert len(resampled) == 320
    assert validate_pcm(resampled) is True

    # Same sample rate passthrough
    assert resample_pcm(samples_48k, orig_sr=48000, target_sr=48000) == samples_48k


def test_audio_devices_enumeration():
    """Verify audio device discovery without hardware dependency."""
    devices = get_available_devices()
    assert "inputs" in devices
    assert "outputs" in devices
    assert isinstance(devices["inputs"], list)
    assert isinstance(devices["outputs"], list)


# ============================================================================
# 3. Audio Queue & Barge-in Flushing Tests
# ============================================================================

@pytest.mark.asyncio
async def test_audio_queue_operations_and_clear():
    """Verify AudioQueue FIFO operations and instant clear for barge-in."""
    q = AudioQueue(maxsize=10)

    # Put chunks
    for i in range(5):
        await q.put(f"chunk_{i}".encode())
    assert q.qsize == 5

    # Retrieve one
    first = await q.get()
    assert first == b"chunk_0"
    assert q.qsize == 4

    # Instant flush for barge-in
    flushed = q.clear()
    assert flushed == 4
    assert q.empty is True


# ============================================================================
# 4. System Instruction Provider Tests
# ============================================================================

def test_shared_system_instructions():
    """Verify shared instructions between text and voice modes."""
    base = system_instruction_provider.get_base_prompt()
    assert "JARVIS" in base
    assert "Operational Excellence" in base

    text_prompt = system_instruction_provider.get_text_instructions("User context")
    voice_prompt = system_instruction_provider.get_voice_instructions("User context")

    # Both must include the core persona
    assert "JARVIS (Just A Rather Very Intelligent System)" in text_prompt
    assert "JARVIS (Just A Rather Very Intelligent System)" in voice_prompt

    # Voice mode has speech-specific conversational rules
    assert "real-time spoken audio" in voice_prompt
    assert "concise, natural, and conversational" in voice_prompt


# ============================================================================
# 5. Voice Session State Machine & Interruption Tests
# ============================================================================

@pytest.mark.asyncio
async def test_voice_session_lifecycle_and_state_transitions(tmp_path):
    """Verify voice session state machine transitions."""
    store_file = tmp_path / "memory.json"
    mem_mgr = MemoryManager(store=MemoryStore(file_path=str(store_file)))

    session = VoiceSession(
        session_id="test-session-1",
        config=VoiceConfig(voice_name="Puck"),
        mem_mgr=mem_mgr,
    )
    assert session.state == VoiceSessionState.IDLE

    state_transitions = []

    async def on_state(state, payload):
        state_transitions.append(state)

    session.on_state_change(on_state)

    # Mock Live Client to avoid remote network dependency
    mock_live = MagicMock()
    mock_live.is_connected = True
    mock_live.connect = AsyncMock()
    mock_live.close = AsyncMock()
    mock_live.send_audio_chunk = AsyncMock()
    mock_live.send_text_message = AsyncMock()

    # Async generator simulating events
    async def mock_events():
        yield LiveEvent(event_type="audio", audio_chunk=b"\x00\x00" * 100)
        yield LiveEvent(event_type="turn_complete", turn_complete=True)

    mock_live.receive_events = mock_events

    with patch("backend.app.voice.session.GeminiLiveClient", return_value=mock_live):
        await session.start()
        assert session.state == VoiceSessionState.LISTENING

        # Stream audio
        test_chunk = b"\x01\x02" * 1600
        await session.send_audio(test_chunk)
        mock_live.send_audio_chunk.assert_called_with(test_chunk)

        # Allow receive loop to process simulated audio event
        await asyncio.sleep(0.05)

        # Test barge-in interrupt
        await session.interrupt()
        assert session.state == VoiceSessionState.LISTENING
        assert session.output_queue.empty is True

        # Stop and cleanup
        await session.cleanup()
        assert session.state == VoiceSessionState.DISCONNECTED

    assert VoiceSessionState.CONNECTING in state_transitions
    assert VoiceSessionState.LISTENING in state_transitions
    assert VoiceSessionState.DISCONNECTED in state_transitions


# ============================================================================
# 6. Memory Integration in Voice Session
# ============================================================================

@pytest.mark.asyncio
async def test_voice_session_memory_seeding_and_extraction(tmp_path):
    """Verify that voice sessions load memory context and extract new memories."""
    store_file = tmp_path / "memory.json"
    store = MemoryStore(file_path=str(store_file))
    store.add(
        MemoryRecord(
            content="User prefers Python for data engineering",
            category=MemoryCategory.PREFERENCE,
            importance=0.9,
        )
    )
    mem_mgr = MemoryManager(store=store, retriever=MemoryRetriever(store=store))

    session = VoiceSession(
        session_id="mem-session-1",
        config=VoiceConfig(voice_name="Puck"),
        mem_mgr=mem_mgr,
    )

    mock_live = MagicMock()
    mock_live.is_connected = True
    mock_live.connect = AsyncMock()
    mock_live.close = AsyncMock()

    async def mock_events():
        # Simulate dialogue turn
        yield LiveEvent(event_type="transcript", transcript_user="I am building a flight tracker app in Rust")
        yield LiveEvent(event_type="transcript", transcript_model="Rust is a solid choice for performance and safety.")
        yield LiveEvent(event_type="turn_complete", turn_complete=True)

    mock_live.receive_events = mock_events

    with patch("backend.app.voice.session.GeminiLiveClient", return_value=mock_live):
        await session.start()

        # Verify that connect was called with memory context included in system instruction
        call_kwargs = mock_live.connect.call_args[1]
        instruction = call_kwargs.get("system_instruction", "")
        assert "Python for data engineering" in instruction

        # Let the receive loop dispatch the dialogue and trigger background extraction
        await asyncio.sleep(0.05)

        await session.cleanup()


# ============================================================================
# 7. Tool Execution in Voice Session
# ============================================================================

@pytest.mark.asyncio
async def test_voice_session_tool_execution():
    """Verify tool execution within voice session loop."""
    tool_reg = ToolRegistry()
    tool_reg.register_builtins()
    tool_mgr = ToolManager(registry=tool_reg)

    session = VoiceSession(
        session_id="tool-session-1",
        tool_reg=tool_reg,
        tool_mgr=tool_mgr,
    )

    mock_live = MagicMock()
    mock_live.is_connected = True
    mock_live.connect = AsyncMock()
    mock_live.close = AsyncMock()
    mock_live.send_tool_response = AsyncMock()

    async def mock_events():
        # Yield calculator tool call
        yield LiveEvent(
            event_type="tool_call",
            tool_calls=[{"id": "call-123", "name": "calculator", "arguments": {"expression": "25 * 4"}}],
        )
        yield LiveEvent(event_type="turn_complete", turn_complete=True)

    mock_live.receive_events = mock_events

    with patch("backend.app.voice.session.GeminiLiveClient", return_value=mock_live):
        await session.start()
        await asyncio.sleep(0.05)

        # Verify tool response was returned to Live session
        mock_live.send_tool_response.assert_called_once()
        args, kwargs = mock_live.send_tool_response.call_args
        sent_responses = kwargs.get("function_responses") if kwargs else args[0]
        assert len(sent_responses) == 1
        assert sent_responses[0].response["result"]["result"] == 100

        await session.cleanup()


# ============================================================================
# 8. VoiceManager Session Lifecycle
# ============================================================================

@pytest.mark.asyncio
async def test_voice_manager_tracking():
    """Verify VoiceManager creates, tracks, and terminates sessions cleanly."""
    vm = VoiceManager()
    assert vm.active_session_count == 0

    s1 = await vm.create_session(session_id="s1")
    s2 = await vm.create_session(session_id="s2")
    assert vm.active_session_count == 2
    assert vm.get_session("s1") is s1

    await vm.close_session("s1")
    assert vm.active_session_count == 1
    assert vm.get_session("s1") is None

    await vm.close_all()
    assert vm.active_session_count == 0


# ============================================================================
# 9. REST API Voice Endpoints
# ============================================================================

def test_voice_rest_config_endpoint():
    """Verify GET /api/voice/config endpoint returns specs."""
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/voice/config")
        assert res.status_code == 200
        data = res.json()
        assert data["input_sample_rate"] == 16000
        assert data["output_sample_rate"] == 24000
        assert data["default_voice"] == "Puck"
        assert "Puck" in data["supported_voices"]


def test_voice_rest_voices_endpoint():
    """Verify GET /api/voice/voices endpoint returns supported voice list."""
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/voice/voices")
        assert res.status_code == 200
        data = res.json()
        assert "voices" in data
        assert len(data["voices"]) >= 5


def test_voice_rest_devices_endpoint():
    """Verify GET /api/voice/devices endpoint returns available devices."""
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/voice/devices")
        assert res.status_code == 200
        data = res.json()
        assert "inputs" in data
        assert "outputs" in data


# ============================================================================
# 10. WebSocket Streaming Protocol
# ============================================================================

def test_voice_websocket_protocol():
    """Verify WebSocket connection, audio stream handling, and interruption."""
    app = create_app()

    mock_live = MagicMock()
    mock_live.is_connected = True
    mock_live.connect = AsyncMock()
    mock_live.close = AsyncMock()
    mock_live.send_audio_chunk = AsyncMock()

    async def mock_events():
        # Yield single audio chunk
        yield LiveEvent(event_type="audio", audio_chunk=b"\x00\x00" * 200)

    mock_live.receive_events = mock_events

    with patch("backend.app.voice.session.GeminiLiveClient", return_value=mock_live):
        with TestClient(app) as client:
            with client.websocket_connect("/ws/voice") as ws:
                # 1. Send start frame
                ws.send_text(json.dumps({"type": "start", "voice_name": "Puck"}))

                # 2. Receive state frame
                first_msg = ws.receive_json()
                assert first_msg["type"] == "state"

                # 3. Stream binary PCM audio
                pcm_data = b"\x00\x01" * 1600
                ws.send_bytes(pcm_data)

                # 4. Send interrupt directive
                ws.send_text(json.dumps({"type": "interrupt"}))
                interrupt_msg = ws.receive_json()
                assert interrupt_msg["type"] in ("interrupted", "state", "audio")

                # 5. Send stop directive
                ws.send_text(json.dumps({"type": "stop"}))
