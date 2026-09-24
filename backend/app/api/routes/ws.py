import json
import logging
import uuid
from typing import Any, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.schemas.websocket import (
    WebSocketEventType,
    WebSocketInboundMessage,
    WebSocketOutboundMessage,
)
from backend.app.services.connection_manager import ws_manager
from backend.app.services.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main bidirectional WebSocket connection for real-time JARVIS interaction.
    Streams reasoning state, tool calls, and final responses.
    """
    client_id = f"client_{uuid.uuid4().hex[:8]}"
    await ws_manager.connect(client_id, websocket)

    # Send acknowledgment
    await ws_manager.send_message(
        client_id,
        WebSocketOutboundMessage(
            type=WebSocketEventType.CONNECTION_ACK,
            payload={
                "client_id": client_id,
                "status": "connected",
                "message": "JARVIS neural link established",
            }
        )
    )

    orchestrator: AgentOrchestrator = websocket.app.state.orchestrator

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                msg_type = data.get("type")
                payload = data.get("payload", {})
            except Exception as parse_err:
                logger.warning(f"Malformed WebSocket message from {client_id}: {parse_err}")
                await ws_manager.send_message(
                    client_id,
                    WebSocketOutboundMessage(
                        type=WebSocketEventType.ERROR,
                        payload={"error": f"Invalid JSON format: {str(parse_err)}"}
                    )
                )
                continue

            # Heartbeat Ping / Pong
            if msg_type == WebSocketEventType.PING:
                await ws_manager.send_message(
                    client_id,
                    WebSocketOutboundMessage(type=WebSocketEventType.PONG, payload={})
                )
                continue

            # User prompt / message
            elif msg_type == WebSocketEventType.USER_MESSAGE:
                user_text = payload.get("content", "").strip()
                session_id = payload.get("session_id")
                permission = payload.get("caller_permission", "admin")

                if not user_text:
                    await ws_manager.send_message(
                        client_id,
                        WebSocketOutboundMessage(
                            type=WebSocketEventType.ERROR,
                            payload={"error": "Message content cannot be empty"}
                        )
                    )
                    continue

                # Callback to stream events to this specific client
                async def stream_callback(event_name: str, event_data: Dict[str, Any]):
                    try:
                        ev_type = WebSocketEventType(event_name)
                    except ValueError:
                        ev_type = WebSocketEventType.AGENT_THINKING

                    await ws_manager.send_message(
                        client_id,
                        WebSocketOutboundMessage(type=ev_type, payload=event_data)
                    )

                try:
                    # Run reasoning loop with live event streaming
                    response = await orchestrator.run_loop(
                        user_message=user_text,
                        session_id=session_id,
                        caller_permission=permission,
                        event_callback=stream_callback,
                    )

                    # Send final agent message
                    await ws_manager.send_message(
                        client_id,
                        WebSocketOutboundMessage(
                            type=WebSocketEventType.AGENT_MESSAGE,
                            payload={
                                "reply": response.reply,
                                "session_id": response.session_id,
                                "tool_executions": [t.model_dump() for t in response.tool_executions],
                                "llm_provider": response.llm_provider,
                            }
                        )
                    )

                except Exception as loop_err:
                    logger.error(f"Error executing agent loop for {client_id}: {loop_err}", exc_info=True)
                    await ws_manager.send_message(
                        client_id,
                        WebSocketOutboundMessage(
                            type=WebSocketEventType.ERROR,
                            payload={"error": f"Agent reasoning error: {str(loop_err)}"}
                        )
                    )

            else:
                logger.warning(f"Unhandled WebSocket message type: {msg_type}")

    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
    except Exception as exc:
        logger.error(f"Unexpected WebSocket error with {client_id}: {exc}", exc_info=True)
        ws_manager.disconnect(client_id)
