"""VoiceSession orchestrator managing state, audio queues, barge-in, memory, and tools."""

import asyncio
import logging
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional
from google.genai import types

from backend.app.core.prompt_provider import system_instruction_provider
from backend.app.memory.manager import MemoryManager, memory_manager
from backend.app.tools.manager import ToolManager, tool_manager
from backend.app.tools.registry import ToolRegistry, tool_registry
from backend.app.voice.audio import AudioQueue, validate_pcm
from backend.app.voice.config import VoiceConfig, VoiceSessionState
from backend.app.voice.live_client import GeminiLiveClient, LiveEvent

logger = logging.getLogger(__name__)

# Callback type definitions
StateChangeCallback = Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]]
AudioChunkCallback = Callable[[bytes], Coroutine[Any, Any, None]]
TranscriptCallback = Callable[[str, str], Coroutine[Any, Any, None]]


class VoiceSession:
    """Manages an active real-time voice interaction session for a user."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        config: Optional[VoiceConfig] = None,
        mem_mgr: Optional[MemoryManager] = None,
        tool_reg: Optional[ToolRegistry] = None,
        tool_mgr: Optional[ToolManager] = None,
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.config = config or VoiceConfig()
        self.mem_mgr = mem_mgr or memory_manager
        self.tool_reg = tool_reg or tool_registry
        self.tool_mgr = tool_mgr or tool_manager

        self.state: str = VoiceSessionState.IDLE
        self.input_queue = AudioQueue(maxsize=150)
        self.output_queue = AudioQueue(maxsize=300)

        self.live_client: Optional[GeminiLiveClient] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._is_active = False

        # Accumulators for dialog transcript and memory extraction
        self._current_user_transcript: List[str] = []
        self._current_model_transcript: List[str] = []

        # Event callbacks
        self._state_callbacks: List[StateChangeCallback] = []
        self._audio_callbacks: List[AudioChunkCallback] = []
        self._transcript_callbacks: List[TranscriptCallback] = []

    def on_state_change(self, callback: StateChangeCallback) -> None:
        """Register a callback for session state transitions."""
        self._state_callbacks.append(callback)

    def on_audio_chunk(self, callback: AudioChunkCallback) -> None:
        """Register a callback invoked when a 24kHz audio chunk is ready for output."""
        self._audio_callbacks.append(callback)

    def on_transcript(self, callback: TranscriptCallback) -> None:
        """Register a callback for dialog transcripts."""
        self._transcript_callbacks.append(callback)

    async def _set_state(self, new_state: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Update session state and notify subscribers."""
        if self.state == new_state:
            return

        self.state = new_state
        payload = {"session_id": self.session_id, "state": self.state, **(details or {})}
        logger.info(f"VoiceSession [{self.session_id}] -> {self.state}")

        for cb in self._state_callbacks:
            try:
                await cb(new_state, payload)
            except Exception as e:
                logger.warning(f"Error in voice state callback: {e}")

    async def start(self, initial_query: str = "") -> None:
        """Initialize and start the voice session."""
        if self._is_active:
            logger.warning(f"VoiceSession [{self.session_id}] is already active.")
            return

        await self._set_state(VoiceSessionState.CONNECTING)
        self._is_active = True

        try:
            # 1. Retrieve relevant Phase 2 memories to seed the context
            memory_context, _ = self.mem_mgr.build_memory_context(
                initial_query or "user personal preferences and project context",
                limit=5,
            )

            # 2. Build voice instructions using shared SystemInstructionProvider
            system_instruction = system_instruction_provider.get_voice_instructions(memory_context)

            # 3. Retrieve registered tools
            tools = self.tool_reg.get_gemini_tools()

            # 4. Instantiate and connect Live Client
            self.live_client = GeminiLiveClient(
                config=self.config,
                tools=tools,
            )
            await self.live_client.connect(system_instruction=system_instruction)

            # 5. Start asynchronous receive task
            self._receive_task = asyncio.create_task(self._receive_loop())

            await self._set_state(VoiceSessionState.LISTENING)
            logger.info(f"VoiceSession [{self.session_id}] started successfully.")

        except Exception as e:
            logger.error(f"Failed to start VoiceSession [{self.session_id}]: {e}", exc_info=True)
            await self._set_state(VoiceSessionState.ERROR, {"error": str(e)})
            await self.cleanup()
            raise

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """Push an incoming 16kHz PCM audio chunk to the live Gemini session."""
        if not self._is_active or not self.live_client or not self.live_client.is_connected:
            return

        if not validate_pcm(pcm_bytes):
            return

        try:
            # If user begins speaking while speaking, trigger barge-in locally
            if self.state == VoiceSessionState.SPEAKING:
                await self.interrupt()

            await self.live_client.send_audio_chunk(pcm_bytes)
        except Exception as e:
            logger.error(f"Error streaming audio in session [{self.session_id}]: {e}")

    async def send_text(self, text: str) -> None:
        """Send a text prompt directly into the active voice stream."""
        if not self._is_active or not self.live_client or not self.live_client.is_connected:
            return

        await self._set_state(VoiceSessionState.THINKING)
        self._current_user_transcript.append(text)
        await self._notify_transcript("user", text)
        await self.live_client.send_text_message(text)

    async def interrupt(self) -> None:
        """Immediate barge-in: flush output audio queue and notify client to halt speaker."""
        drained = self.output_queue.clear()
        logger.info(f"VoiceSession [{self.session_id}] interrupted: flushed {drained} chunks")
        await self._set_state(VoiceSessionState.INTERRUPTED)
        # Revert immediately back to LISTENING
        await self._set_state(VoiceSessionState.LISTENING)

    async def _notify_transcript(self, role: str, text: str) -> None:
        """Notify subscribers of conversation transcripts."""
        for cb in self._transcript_callbacks:
            try:
                await cb(role, text)
            except Exception as e:
                logger.warning(f"Error in transcript callback: {e}")

    async def _receive_loop(self) -> None:
        """Background loop receiving and dispatching Gemini Live events."""
        if not self.live_client:
            return

        try:
            async for event in self.live_client.receive_events():
                if not self._is_active:
                    break

                # 1. Barge-in interruption signaled by Gemini
                if event.interrupted:
                    await self.interrupt()

                # 2. Incoming audio response chunk (24kHz PCM)
                elif event.type == "audio" and event.audio_chunk:
                    if self.state != VoiceSessionState.SPEAKING:
                        await self._set_state(VoiceSessionState.SPEAKING)

                    # Enqueue chunk
                    await self.output_queue.put(event.audio_chunk)

                    # Dispatch to subscribers
                    for cb in self._audio_callbacks:
                        try:
                            await cb(event.audio_chunk)
                        except Exception as e:
                            logger.warning(f"Error in audio chunk callback: {e}")

                # 3. Model turn text or transcript
                elif event.type == "text" and event.text:
                    self._current_model_transcript.append(event.text)
                    await self._notify_transcript("assistant", event.text)

                elif event.type == "transcript":
                    if event.transcript_user:
                        self._current_user_transcript.append(event.transcript_user)
                        await self._notify_transcript("user", event.transcript_user)
                    if event.transcript_model:
                        self._current_model_transcript.append(event.transcript_model)
                        await self._notify_transcript("assistant", event.transcript_model)

                # 4. Tool execution
                elif event.type == "tool_call" and event.tool_calls:
                    await self._set_state(VoiceSessionState.THINKING)
                    responses = []
                    for tc in event.tool_calls:
                        name = tc.get("name")
                        args = tc.get("arguments", {})
                        call_id = tc.get("id")

                        logger.info(f"VoiceSession executing tool '{name}' with args {args}")
                        info = self.tool_mgr.execute_tool(tool_name=name, arguments=args)
                        responses.append(
                            types.FunctionResponse(
                                name=name,
                                id=call_id,
                                response={"result": info.result},
                            )
                        )

                    # Return tool results to Gemini Live
                    if responses and self.live_client:
                        await self.live_client.send_tool_response(function_responses=responses)

                # 5. Turn completion
                elif event.type == "turn_complete":
                    await self._set_state(VoiceSessionState.LISTENING)

                    # Trigger non-blocking Phase 2 memory extraction from recent turn
                    user_utterance = " ".join(self._current_user_transcript).strip()
                    model_utterance = " ".join(self._current_model_transcript).strip()

                    if user_utterance and model_utterance:
                        asyncio.create_task(
                            self._extract_memory_background(user_utterance, model_utterance)
                        )
                        self._current_user_transcript.clear()
                        self._current_model_transcript.clear()

                # 6. Error event
                elif event.type == "error":
                    logger.error(f"VoiceSession received error event: {event.text}")
                    await self._set_state(VoiceSessionState.ERROR, {"error": event.text})

        except asyncio.CancelledError:
            logger.info(f"VoiceSession [{self.session_id}] receive loop stopped.")
        except Exception as e:
            logger.error(f"VoiceSession receive loop error: {e}", exc_info=True)
            await self._set_state(VoiceSessionState.ERROR, {"error": str(e)})

    async def _extract_memory_background(self, user_text: str, model_text: str) -> None:
        """Non-blocking memory extraction triggered by voice dialogues."""
        try:
            # MemoryManager runs extraction safely without blocking audio
            loop = asyncio.get_running_loop()
            saved = await loop.run_in_executor(
                None,
                self.mem_mgr.extract_and_save_memories,
                user_text,
                model_text,
            )
            if saved:
                logger.info(f"Voice session extracted {len(saved)} new memories from conversation")
        except Exception as e:
            logger.warning(f"Background voice memory extraction failed: {e}")

    async def cleanup(self) -> None:
        """Terminate all background tasks, close Gemini connection, and purge audio queues."""
        self._is_active = False

        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self.live_client:
            await self.live_client.close()
            self.live_client = None

        self.input_queue.clear()
        self.output_queue.clear()

        await self._set_state(VoiceSessionState.DISCONNECTED)
        logger.info(f"VoiceSession [{self.session_id}] cleaned up.")
