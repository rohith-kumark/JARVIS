import logging
from typing import Dict
from fastapi import WebSocket
from backend.app.schemas.websocket import WebSocketOutboundMessage

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages active WebSocket client connections, heartbeat pings,
    and event dispatches.
    """

    def __init__(self):
        self._active_connections: Dict[str, WebSocket] = {}

    @property
    def connection_count(self) -> int:
        return len(self._active_connections)

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """Accept and register incoming WebSocket connection."""
        await websocket.accept()
        self._active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id} (Total: {self.connection_count})")

    def disconnect(self, client_id: str) -> None:
        """Remove disconnected client from active registry."""
        if client_id in self._active_connections:
            del self._active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id} (Total: {self.connection_count})")

    async def send_message(self, client_id: str, message: WebSocketOutboundMessage) -> bool:
        """Send structured message to a specific client."""
        ws = self._active_connections.get(client_id)
        if not ws:
            logger.warning(f"Cannot send to client {client_id}: Not connected")
            return False

        try:
            await ws.send_text(message.to_json())
            return True
        except Exception as exc:
            logger.warning(f"Failed to send to client {client_id}: {exc}")
            self.disconnect(client_id)
            return False

    async def broadcast(self, message: WebSocketOutboundMessage) -> None:
        """Broadcast structured message to all active clients."""
        payload_text = message.to_json()
        disconnected_clients = []

        for cid, ws in self._active_connections.items():
            try:
                await ws.send_text(payload_text)
            except Exception as exc:
                logger.warning(f"Broadcast error for {cid}: {exc}")
                disconnected_clients.append(cid)

        for cid in disconnected_clients:
            self.disconnect(cid)


# Global singleton connection manager
ws_manager = WebSocketConnectionManager()
