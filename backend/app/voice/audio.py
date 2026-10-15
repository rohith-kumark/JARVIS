"""Audio processing utilities, PCM validation, and hardware device interfaces for JARVIS."""

import asyncio
import base64
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
import numpy as np

from backend.app.voice.config import (
    AUDIO_CHANNELS,
    BYTES_PER_SAMPLE,
    INPUT_CHUNK_BYTES,
    INPUT_SAMPLE_RATE,
    OUTPUT_SAMPLE_RATE,
)

logger = logging.getLogger(__name__)

# Attempt sounddevice import with fallback
_sd_available = False
try:
    import sounddevice as sd
    _sd_available = True
except Exception as e:
    logger.warning(f"sounddevice hardware interface not available: {e}")
    sd = None


def is_sounddevice_available() -> bool:
    """Check if sounddevice is available and functional."""
    return _sd_available and sd is not None


def pcm_to_base64(pcm_data: bytes) -> str:
    """Encode raw PCM bytes to base64 string for WebSocket transmission."""
    return base64.b64encode(pcm_data).decode("utf-8")


def base64_to_pcm(b64_str: str) -> bytes:
    """Decode base64 string to raw PCM bytes."""
    return base64.b64decode(b64_str)


def validate_pcm(pcm_bytes: bytes, bytes_per_sample: int = BYTES_PER_SAMPLE) -> bool:
    """Verify that the byte array aligns with 16-bit PCM sample boundaries."""
    return len(pcm_bytes) > 0 and len(pcm_bytes) % bytes_per_sample == 0


def resample_pcm(
    pcm_bytes: bytes,
    orig_sr: int,
    target_sr: int = INPUT_SAMPLE_RATE,
) -> bytes:
    """Resample 16-bit mono PCM bytes to target sample rate using numpy interpolation."""
    if orig_sr == target_sr:
        return pcm_bytes

    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    if len(samples) == 0:
        return b""

    duration = len(samples) / orig_sr
    target_length = int(round(duration * target_sr))
    if target_length == 0:
        return b""

    orig_indices = np.linspace(0, len(samples) - 1, num=len(samples))
    target_indices = np.linspace(0, len(samples) - 1, num=target_length)
    resampled = np.interp(target_indices, orig_indices, samples).astype(np.int16)
    return resampled.tobytes()


def get_available_devices() -> Dict[str, List[Dict[str, Any]]]:
    """Query and return available audio input and output devices."""
    if not is_sounddevice_available():
        return {
            "inputs": [{"id": 0, "name": "Default Virtual Microphone (Simulated)", "channels": 1}],
            "outputs": [{"id": 0, "name": "Default Virtual Speaker (Simulated)", "channels": 1}],
        }

    inputs = []
    outputs = []
    try:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            name = dev.get("name", f"Device {idx}")
            max_in = dev.get("max_input_channels", 0)
            max_out = dev.get("max_output_channels", 0)

            if max_in > 0:
                inputs.append({"id": idx, "name": name, "channels": max_in, "default_sr": dev.get("default_samplerate", 16000)})
            if max_out > 0:
                outputs.append({"id": idx, "name": name, "channels": max_out, "default_sr": dev.get("default_samplerate", 24000)})
    except Exception as e:
        logger.warning(f"Error querying audio devices: {e}")
        inputs = [{"id": 0, "name": "Default Microphone", "channels": 1}]
        outputs = [{"id": 0, "name": "Default Speaker", "channels": 1}]

    return {"inputs": inputs, "outputs": outputs}


class AudioQueue:
    """Asynchronous bounded queue for streaming audio chunks with immediate flush/drain."""

    def __init__(self, maxsize: int = 200) -> None:
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=maxsize)

    async def put(self, chunk: bytes) -> None:
        """Enqueue audio chunk, dropping oldest if queue is full to avoid memory accumulation."""
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self._queue.put(chunk)

    def put_nowait(self, chunk: bytes) -> None:
        """Enqueue audio chunk immediately without awaiting."""
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            self._queue.put_nowait(chunk)
        except asyncio.QueueFull:
            pass

    async def get(self) -> bytes:
        """Retrieve next audio chunk."""
        return await self._queue.get()

    def get_nowait(self) -> Optional[bytes]:
        """Retrieve next audio chunk immediately if available."""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def clear(self) -> int:
        """Instantly flush all buffered audio chunks (used during barge-in/interruption)."""
        drained = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        return drained

    @property
    def qsize(self) -> int:
        return self._queue.qsize()

    @property
    def empty(self) -> bool:
        return self._queue.empty()


class MicrophoneStream:
    """Captures 16kHz 16-bit mono PCM audio from local microphone via sounddevice."""

    def __init__(
        self,
        sample_rate: int = INPUT_SAMPLE_RATE,
        chunk_bytes: int = INPUT_CHUNK_BYTES,
        device: Optional[int] = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.chunk_bytes = chunk_bytes
        self.device = device
        self.queue: AudioQueue = AudioQueue(maxsize=100)
        self._stream: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False

    def _audio_callback(self, indata: bytes, frames: int, time_info: Any, status: Any) -> None:
        """Audio hardware callback invoked from the sounddevice thread."""
        if status:
            logger.warning(f"Microphone input status: {status}")
        if self._running and self._loop and self._loop.is_running():
            chunk = bytes(indata)
            self._loop.call_soon_threadsafe(self.queue.put_nowait, chunk)

    async def start(self) -> None:
        """Start microphone capture stream."""
        if not is_sounddevice_available():
            raise RuntimeError("Microphone hardware access not available: sounddevice not loaded.")

        self._loop = asyncio.get_running_loop()
        self._running = True

        frames_per_chunk = self.chunk_bytes // (BYTES_PER_SAMPLE * AUDIO_CHANNELS)

        try:
            self._stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=frames_per_chunk,
                device=self.device,
                channels=AUDIO_CHANNELS,
                dtype="int16",
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info(f"MicrophoneStream started ({self.sample_rate}Hz, 16-bit mono, blocksize={frames_per_chunk})")
        except Exception as e:
            self._running = False
            logger.error(f"Failed to open microphone stream: {e}")
            raise RuntimeError(f"Microphone initialization failure: {e}")

    async def stop(self) -> None:
        """Stop and close microphone stream."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error closing microphone stream: {e}")
            finally:
                self._stream = None
        self.queue.clear()
        logger.info("MicrophoneStream stopped and closed")

    async def read_chunk(self) -> bytes:
        """Read the next captured 16kHz PCM audio chunk."""
        return await self.queue.get()


class SpeakerPlayback:
    """Plays 24kHz 16-bit mono PCM audio through local speakers via sounddevice."""

    def __init__(
        self,
        sample_rate: int = OUTPUT_SAMPLE_RATE,
        device: Optional[int] = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.device = device
        self.queue: AudioQueue = AudioQueue(maxsize=300)
        self._stream: Optional[Any] = None
        self._running = False

    def _audio_callback(self, outdata: bytearray, frames: int, time_info: Any, status: Any) -> None:
        """Audio hardware callback invoked to fill speaker buffer."""
        if status:
            logger.warning(f"Speaker output status: {status}")

        bytes_needed = frames * BYTES_PER_SAMPLE * AUDIO_CHANNELS
        chunk = self.queue.get_nowait()
        if chunk and len(chunk) >= bytes_needed:
            outdata[:] = chunk[:bytes_needed]
        elif chunk:
            outdata[:len(chunk)] = chunk
            outdata[len(chunk):] = b"\x00" * (bytes_needed - len(chunk))
        else:
            outdata[:] = b"\x00" * bytes_needed

    async def start(self) -> None:
        """Start speaker playback stream."""
        if not is_sounddevice_available():
            raise RuntimeError("Speaker hardware access not available: sounddevice not loaded.")

        self._running = True
        try:
            self._stream = sd.RawOutputStream(
                samplerate=self.sample_rate,
                device=self.device,
                channels=AUDIO_CHANNELS,
                dtype="int16",
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info(f"SpeakerPlayback started ({self.sample_rate}Hz, 16-bit mono)")
        except Exception as e:
            self._running = False
            logger.error(f"Failed to open speaker playback stream: {e}")
            raise RuntimeError(f"Speaker initialization failure: {e}")

    async def stop(self) -> None:
        """Stop and close speaker playback stream."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error closing speaker stream: {e}")
            finally:
                self._stream = None
        self.queue.clear()
        logger.info("SpeakerPlayback stopped")

    def interrupt(self) -> int:
        """Instantly flush all pending playback audio (barge-in)."""
        drained = self.queue.clear()
        logger.info(f"SpeakerPlayback interrupted: drained {drained} queued audio chunks")
        return drained
