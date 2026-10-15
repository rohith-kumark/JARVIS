"""JARVIS Phase 3 Voice Subsystem integrating Gemini Live API."""

from backend.app.voice.config import (
    DEFAULT_CHUNK_MS,
    DEFAULT_LIVE_MODEL,
    DEFAULT_VOICE,
    FALLBACK_LIVE_MODELS,
    INPUT_CHUNK_BYTES,
    INPUT_SAMPLE_RATE,
    OUTPUT_CHUNK_BYTES,
    OUTPUT_SAMPLE_RATE,
    SUPPORTED_VOICES,
    VoiceConfig,
    VoiceSessionState,
)
from backend.app.voice.audio import (
    AudioQueue,
    MicrophoneStream,
    SpeakerPlayback,
    base64_to_pcm,
    get_available_devices,
    is_sounddevice_available,
    pcm_to_base64,
    resample_pcm,
    validate_pcm,
)
from backend.app.voice.live_client import GeminiLiveClient, LiveEvent
from backend.app.voice.session import VoiceSession
from backend.app.voice.manager import VoiceManager, voice_manager

__all__ = [
    "DEFAULT_CHUNK_MS",
    "DEFAULT_LIVE_MODEL",
    "DEFAULT_VOICE",
    "FALLBACK_LIVE_MODELS",
    "INPUT_CHUNK_BYTES",
    "INPUT_SAMPLE_RATE",
    "OUTPUT_CHUNK_BYTES",
    "OUTPUT_SAMPLE_RATE",
    "SUPPORTED_VOICES",
    "VoiceConfig",
    "VoiceSessionState",
    "AudioQueue",
    "MicrophoneStream",
    "SpeakerPlayback",
    "base64_to_pcm",
    "get_available_devices",
    "is_sounddevice_available",
    "pcm_to_base64",
    "resample_pcm",
    "validate_pcm",
    "GeminiLiveClient",
    "LiveEvent",
    "VoiceSession",
    "VoiceManager",
    "voice_manager",
]
