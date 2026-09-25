"""Voice subsystem configuration and constants for JARVIS Phase 3."""

from typing import List, Optional
from pydantic import BaseModel, Field

# Gemini Live supported voice personas
SUPPORTED_VOICES: List[str] = ["Puck", "Charon", "Kore", "Fenrir", "Aoede"]
DEFAULT_VOICE: str = "Puck"

# Audio technical specifications
INPUT_SAMPLE_RATE: int = 16000     # 16 kHz PCM
OUTPUT_SAMPLE_RATE: int = 24000    # 24 kHz PCM
AUDIO_CHANNELS: int = 1            # Mono
BYTES_PER_SAMPLE: int = 2          # 16-bit PCM (2 bytes per sample)
DEFAULT_CHUNK_MS: int = 100        # 100 ms audio chunk duration

# 100ms chunk at 16kHz = 1600 samples = 3200 bytes
INPUT_CHUNK_BYTES: int = (INPUT_SAMPLE_RATE * DEFAULT_CHUNK_MS // 1000) * BYTES_PER_SAMPLE
# 100ms chunk at 24kHz = 2400 samples = 4800 bytes
OUTPUT_CHUNK_BYTES: int = (OUTPUT_SAMPLE_RATE * DEFAULT_CHUNK_MS // 1000) * BYTES_PER_SAMPLE

# Default Gemini Live streaming model
DEFAULT_LIVE_MODEL: str = "gemini-2.5-flash-native-audio-latest"
FALLBACK_LIVE_MODELS: List[str] = [
    "gemini-2.5-flash-native-audio-latest",
    "gemini-2.5-flash-native-audio-preview-12-2025",
    "gemini-2.5-flash",
]


class VoiceConfig(BaseModel):
    """Configuration for an active voice session."""

    voice_name: str = Field(default=DEFAULT_VOICE, description="Gemini voice persona")
    model: str = Field(default=DEFAULT_LIVE_MODEL, description="Gemini Live streaming model")
    input_sample_rate: int = Field(default=INPUT_SAMPLE_RATE, description="Input sample rate (Hz)")
    output_sample_rate: int = Field(default=OUTPUT_SAMPLE_RATE, description="Output sample rate (Hz)")
    channels: int = Field(default=AUDIO_CHANNELS, description="Channel count (1=mono)")
    input_device: Optional[int] = Field(default=None, description="Input device index for local audio")
    output_device: Optional[int] = Field(default=None, description="Output device index for local audio")


class VoiceSessionState(str):
    """Voice session operational states."""

    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"
    DISCONNECTED = "DISCONNECTED"
