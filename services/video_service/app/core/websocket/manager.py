import json
import logging
import time
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class LiveStreamConnectionManager:
    """
    Manages active WebSocket connections for Live Streaming with bidirectional heartbeat monitoring.

    Tracks active connections per `stream_id` and records heartbeat timestamps to detect
    dead connections and network drops.
    """

    def __init__(self, heartbeat_timeout_seconds: float = 25.0) -> None:
        # stream_id -> {client_id: WebSocket}
        self._streams: dict[str, dict[str, WebSocket]] = {}
        # client_id -> last_heartbeat_timestamp
        self._last_heartbeat: dict[str, float] = {}
        # client_id -> stream_id
        self._client_stream: dict[str, str] = {}
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds

    async def connect(
        self, websocket: WebSocket, stream_id: str, client_id: str
    ) -> None:
        """Accept WebSocket connection and register client in stream pool."""
        await websocket.accept()

        if stream_id not in self._streams:
            self._streams[stream_id] = {}

        self._streams[stream_id][client_id] = websocket
        self._last_heartbeat[client_id] = time.time()
        self._client_stream[client_id] = stream_id

        logger.info(
            "WebSocket client %s connected to live stream %s (total: %d)",
            client_id,
            stream_id,
            len(self._streams[stream_id]),
        )

    def disconnect(self, stream_id: str, client_id: str) -> None:
        """Unregister client from stream connection pool."""
        if stream_id in self._streams:
            self._streams[stream_id].pop(client_id, None)
            if not self._streams[stream_id]:
                self._streams.pop(stream_id, None)

        self._last_heartbeat.pop(client_id, None)
        self._client_stream.pop(client_id, None)

        logger.info(
            "WebSocket client %s disconnected from live stream %s",
            client_id,
            stream_id,
        )

    def record_heartbeat(self, client_id: str) -> None:
        """Update last heartbeat timestamp for client."""
        self._last_heartbeat[client_id] = time.time()

    def is_alive(self, client_id: str) -> bool:
        """Check if client has sent a heartbeat within the timeout window."""
        last = self._last_heartbeat.get(client_id)
        if last is None:
            return False
        return (time.time() - last) <= self.heartbeat_timeout_seconds

    def get_stream_viewer_count(self, stream_id: str) -> int:
        """Return number of currently active connections for stream."""
        return len(self._streams.get(stream_id, {}))

    async def send_json(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """Send JSON payload to a specific WebSocket client."""
        try:
            await websocket.send_text(json.dumps(data, default=str))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to send WebSocket message: %s", exc)

    async def broadcast_to_stream(self, stream_id: str, message: dict[str, Any]) -> int:
        """
        Broadcast message to all active clients connected to stream_id.
        Returns number of clients reached.
        """
        clients = self._streams.get(stream_id, {})
        if not clients:
            return 0

        payload = json.dumps(message, default=str)
        dead_clients: list[str] = []
        sent_count = 0

        for client_id, ws in list(clients.items()):
            try:
                await ws.send_text(payload)
                sent_count += 1
            except Exception:  # noqa: BLE001
                dead_clients.append(client_id)

        # Cleanup any dead sockets discovered during broadcast
        for cid in dead_clients:
            self.disconnect(stream_id, cid)

        return sent_count


live_connection_manager = LiveStreamConnectionManager()
