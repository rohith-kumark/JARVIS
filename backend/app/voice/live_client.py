"""Gemini Live API client abstraction for bidirectional real-time audio streaming."""

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from google import genai
from google.genai import types

from backend.app.core.config import Settings, get_settings
from backend.app.voice.config import (
    DEFAULT_LIVE_MODEL,
    DEFAULT_VOICE,
    FALLBACK_LIVE_MODELS,
    INPUT_SAMPLE_RATE,
    VoiceConfig,
)

logger = logging.getLogger(__name__)


class LiveEvent:
    """Represents an event received from the Gemini Live bidirectional stream."""

    def __init__(
        self,
        event_type: str,
        audio_chunk: Optional[bytes] = None,
        text: Optional[str] = None,
        transcript_user: Optional[str] = None,
        transcript_model: Optional[str] = None,
        interrupted: bool = False,
        turn_complete: bool = False,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        raw_message: Optional[Any] = None,
    ) -> None:
        self.type = event_type  # "audio", "text", "transcript", "interrupted", "turn_complete", "tool_call"
        self.audio_chunk = audio_chunk
        self.text = text
        self.transcript_user = transcript_user
        self.transcript_model = transcript_model
        self.interrupted = interrupted
        self.turn_complete = turn_complete
        self.tool_calls = tool_calls or []
        self.raw_message = raw_message

    def __repr__(self) -> str:
        return f"<LiveEvent type={self.type} interrupted={self.interrupted} turn_complete={self.turn_complete}>"


class GeminiLiveClient:
    """Manages an asynchronous bidirectional streaming session with Gemini Live API."""

    def __init__(
        self,
        config: Optional[VoiceConfig] = None,
        settings: Optional[Settings] = None,
        tools: Optional[List[Any]] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.config = config or VoiceConfig()
        self.tools = tools or []
        self._client: Optional[genai.Client] = None
        self._session: Optional[Any] = None
        self._session_ctx: Optional[Any] = None
        self._connected = False
        self._closed = False
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Google GenAI SDK client."""
        api_key = self.settings.GEMINI_API_KEY
        if api_key and api_key.strip():
            self._client = genai.Client(api_key=api_key)
        else:
            logger.warning("No GEMINI_API_KEY available for GeminiLiveClient.")
            self._client = None

    @property
    def is_connected(self) -> bool:
        return self._connected and self._session is not None

    async def connect(self, system_instruction: str = "") -> None:
        """Establish a live bidirectional streaming connection with Gemini Live API."""
        if not self._client:
            raise RuntimeError("Gemini API key is required to establish a Live Voice session.")

        voice_name = self.config.voice_name or DEFAULT_VOICE
        models_to_try = [self.config.model]
        for fb in FALLBACK_LIVE_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"Connecting to Gemini Live API (model={model}, voice={voice_name})...")
                live_config = types.LiveConnectConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                        )
                    ),
                    system_instruction=types.Content(
                        parts=[types.Part.from_text(text=system_instruction)]
                    ) if system_instruction else None,
                    tools=self.tools if self.tools else None,
                )

                self._session_ctx = self._client.aio.live.connect(model=model, config=live_config)
                self._session = await self._session_ctx.__aenter__()
                self._connected = True
                self._closed = False
                logger.info(f"Connected successfully to Gemini Live session using model '{model}'")
                return
            except Exception as e:
                last_error = e
                logger.warning(f"Failed to connect to Live model '{model}': {e}. Trying next...")

        self._connected = False
        raise RuntimeError(f"Unable to establish Gemini Live session with any candidate model: {last_error}")

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Stream a 16kHz PCM audio chunk to the active Gemini Live session."""
        if not self.is_connected:
            raise RuntimeError("Cannot send audio: Gemini Live session is not connected.")

        blob = types.Blob(data=pcm_bytes, mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}")
        await self._session.send_realtime_input(audio=blob)

    async def send_text_message(self, text: str, end_of_turn: bool = True) -> None:
        """Send a client text turn to the Live session."""
        if not self.is_connected:
            raise RuntimeError("Cannot send text: Gemini Live session is not connected.")

        content = types.Content(role="user", parts=[types.Part.from_text(text=text)])
        await self._session.send_client_content(turns=content, turn_complete=end_of_turn)

    async def send_tool_response(self, function_responses: List[types.FunctionResponse]) -> None:
        """Send tool execution results back to the Gemini Live session."""
        if not self.is_connected:
            raise RuntimeError("Cannot send tool response: Gemini Live session is not connected.")

        await self._session.send_tool_response(function_responses=function_responses)

    async def receive_events(self) -> AsyncIterator[LiveEvent]:
        """Asynchronous generator that yields incoming events from the Gemini Live stream."""
        if not self.is_connected:
            raise RuntimeError("Cannot receive events: Gemini Live session is not connected.")

        try:
            async for message in self._session.receive():
                if self._closed:
                    break

                # 1. Server content (audio, text, interruption, turn_complete)
                if message.server_content:
                    sc = message.server_content

                    # Check for barge-in interruption detected by Gemini
                    if sc.interrupted:
                        yield LiveEvent(event_type="interrupted", interrupted=True, raw_message=message)

                    # Extract output transcript if provided
                    transcript_out = None
                    if sc.output_transcription and hasattr(sc.output_transcription, "text"):
                        transcript_out = sc.output_transcription.text

                    # Extract input transcript if provided
                    transcript_in = None
                    if sc.input_transcription and hasattr(sc.input_transcription, "text"):
                        transcript_in = sc.input_transcription.text

                    if transcript_in or transcript_out:
                        yield LiveEvent(
                            event_type="transcript",
                            transcript_user=transcript_in,
                            transcript_model=transcript_out,
                            raw_message=message,
                        )

                    # Extract model output parts (audio or text)
                    if sc.model_turn and sc.model_turn.parts:
                        for part in sc.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                yield LiveEvent(
                                    event_type="audio",
                                    audio_chunk=part.inline_data.data,
                                    raw_message=message,
                                )
                            if part.text:
                                yield LiveEvent(
                                    event_type="text",
                                    text=part.text,
                                    raw_message=message,
                                )

                    # Check for turn completion
                    if sc.turn_complete:
                        yield LiveEvent(
                            event_type="turn_complete",
                            turn_complete=True,
                            raw_message=message,
                        )

                # 2. Tool function calls
                if message.tool_call and message.tool_call.function_calls:
                    calls = []
                    for fc in message.tool_call.function_calls:
                        calls.append({
                            "id": getattr(fc, "id", None),
                            "name": fc.name,
                            "arguments": fc.args or {},
                        })
                    yield LiveEvent(
                        event_type="tool_call",
                        tool_calls=calls,
                        raw_message=message,
                    )

        except asyncio.CancelledError:
            logger.info("LiveClient receive loop cancelled.")
            raise
        except Exception as e:
            if not self._closed:
                logger.error(f"Error in Gemini Live receive loop: {e}", exc_info=True)
                yield LiveEvent(event_type="error", text=str(e), raw_message=e)

    async def close(self) -> None:
        """Cleanly close the Gemini Live session."""
        if self._closed:
            return

        self._closed = True
        self._connected = False

        if self._session_ctx and self._session:
            try:
                await self._session_ctx.__aexit__(None, None, None)
                logger.info("Gemini Live session closed cleanly.")
            except Exception as e:
                logger.warning(f"Exception during Live session cleanup: {e}")
            finally:
                self._session = None
                self._session_ctx = None
