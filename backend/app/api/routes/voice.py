"""FastAPI routes and WebSocket endpoint for real-time voice interaction (Phase 3)."""

import json
import logging
from typing import Any, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from backend.app.core.config import get_settings
from backend.app.voice.audio import (
    base64_to_pcm,
    get_available_devices,
    pcm_to_base64,
)
from backend.app.voice.config import (
    DEFAULT_CHUNK_MS,
    DEFAULT_LIVE_MODEL,
    DEFAULT_VOICE,
    INPUT_SAMPLE_RATE,
    OUTPUT_SAMPLE_RATE,
    SUPPORTED_VOICES,
    VoiceConfig,
    VoiceSessionState,
)
from backend.app.voice.manager import voice_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/config")
def get_voice_config() -> Dict[str, Any]:
    """Retrieve default voice settings and technical specifications."""
    settings = get_settings()
    return {
        "enabled": settings.VOICE_ENABLED,
        "default_voice": settings.VOICE_NAME or DEFAULT_VOICE,
        "supported_voices": SUPPORTED_VOICES,
        "model": settings.VOICE_MODEL or DEFAULT_LIVE_MODEL,
        "input_sample_rate": INPUT_SAMPLE_RATE,
        "output_sample_rate": OUTPUT_SAMPLE_RATE,
        "channels": settings.VOICE_CHANNELS,
        "chunk_ms": DEFAULT_CHUNK_MS,
    }


@router.get("/voices")
def get_supported_voices() -> Dict[str, Any]:
    """Retrieve list of available voice personas."""
    return {"voices": SUPPORTED_VOICES, "default": DEFAULT_VOICE}


@router.get("/devices")
def get_devices() -> Dict[str, Any]:
    """Enumerate host audio hardware devices."""
    return get_available_devices()


# Standalone WebSocket router to allow mounting at /ws/voice directly
ws_router = APIRouter(tags=["voice-streaming"])


@ws_router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket) -> None:
    """Real-time bidirectional WebSocket bridge for voice streaming:

    Client -> Backend: 16kHz PCM audio chunks or control directives (start, interrupt, stop)
    Backend -> Client: 24kHz PCM audio chunks, state changes, transcripts
    """
    await websocket.accept()
    session = None
    session_id = None
    logger.info("WebSocket client connected to /ws/voice")

    try:
        # Await initial configuration message or use default
        init_message = await websocket.receive_text()
        voice_name = DEFAULT_VOICE
        client_session_id = None

        try:
            parsed = json.loads(init_message)
            if isinstance(parsed, dict) and parsed.get("type") == "start":
                voice_name = parsed.get("voice_name", DEFAULT_VOICE)
                client_session_id = parsed.get("session_id")
        except Exception:
            pass

        # Create session
        vconfig = VoiceConfig(voice_name=voice_name)
        session = await voice_manager.create_session(session_id=client_session_id, config=vconfig)
        session_id = session.session_id

        # Register callbacks to stream back to the WebSocket
        async def on_state_change(new_state: str, payload: Dict[str, Any]) -> None:
            try:
                await websocket.send_json({"type": "state", "state": new_state, "payload": payload})
            except Exception:
                pass

        async def on_audio_chunk(pcm_bytes: bytes) -> None:
            try:
                await websocket.send_json({
                    "type": "audio",
                    "data": pcm_to_base64(pcm_bytes),
                    "sample_rate": OUTPUT_SAMPLE_RATE,
                })
            except Exception:
                pass

        async def on_transcript(role: str, text: str) -> None:
            try:
                await websocket.send_json({"type": "transcript", "role": role, "text": text})
            except Exception:
                pass

        session.on_state_change(on_state_change)
        session.on_audio_chunk(on_audio_chunk)
        session.on_transcript(on_transcript)

        # Start the live session
        await session.start()

        # Listen for messages from client
        while True:
            raw_msg = await websocket.receive()

            # 1. Binary message = raw 16kHz PCM audio
            if "bytes" in raw_msg and raw_msg["bytes"]:
                pcm_data = raw_msg["bytes"]
                await session.send_audio(pcm_data)

            # 2. Text message = JSON directive or base64 audio
            elif "text" in raw_msg and raw_msg["text"]:
                text_data = raw_msg["text"]
                try:
                    payload = json.loads(text_data)
                    msg_type = payload.get("type")

                    if msg_type == "audio" and payload.get("data"):
                        pcm_data = base64_to_pcm(payload["data"])
                        await session.send_audio(pcm_data)

                    elif msg_type == "text" and payload.get("text"):
                        await session.send_text(payload["text"])

                    elif msg_type == "interrupt":
                        logger.info(f"Client requested barge-in interruption for session [{session_id}]")
                        await session.interrupt()
                        await websocket.send_json({"type": "interrupted"})

                    elif msg_type == "stop":
                        logger.info(f"Client requested stop for session [{session_id}]")
                        break

                except json.JSONDecodeError:
                    logger.warning("Received invalid non-JSON text frame on /ws/voice")

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from /ws/voice [{session_id}]")
    except Exception as e:
        logger.error(f"WebSocket voice session error [{session_id}]: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        if session_id:
            await voice_manager.close_session(session_id)
        try:
            await websocket.close()
        except Exception:
            pass
