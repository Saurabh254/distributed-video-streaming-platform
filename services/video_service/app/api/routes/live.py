import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.websocket.manager import live_connection_manager
from app.schemas.events import EventStatus, VideoEventType
from app.workers.publisher import event_publisher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["live-streaming"])


@router.websocket("/ws/{stream_id}")
async def live_stream_websocket(websocket: WebSocket, stream_id: str) -> None:
    """
    WebSocket endpoint for Live Streaming with bidirectional heartbeats.

    Clients send periodic `{"type": "ping", "timestamp": ...}` messages (default: every 10s).
    Server replies with `{"type": "pong", ...}`. If no heartbeat is received within 25s,
    the server terminates the connection to cleanly drop dead streams.
    """
    client_id = f"client-{uuid4().hex[:8]}"
    await live_connection_manager.connect(websocket, stream_id, client_id)

    # Handshake greeting with configuration details
    await live_connection_manager.send_json(
        websocket,
        {
            "type": "connection_established",
            "stream_id": stream_id,
            "client_id": client_id,
            "heartbeat_interval_seconds": 10,
            "heartbeat_timeout_seconds": live_connection_manager.heartbeat_timeout_seconds,
            "viewer_count": live_connection_manager.get_stream_viewer_count(stream_id),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    # Publish stream connection event to Kafka & Redis
    event_publisher.publish_live_event(
        stream_id=stream_id,
        event_type=VideoEventType.LIVE_STREAM_STARTED,
        status=EventStatus.PROCESSING,
        step="client_connected",
        data={
            "client_id": client_id,
            "viewer_count": live_connection_manager.get_stream_viewer_count(stream_id),
        },
    )

    async def heartbeat_check_loop() -> None:
        """Periodically inspect client heartbeat freshness."""
        try:
            while True:
                await asyncio.sleep(5.0)
                if not live_connection_manager.is_alive(client_id):
                    logger.warning(
                        "Heartbeat timeout (>%.1fs) for client %s on stream %s. Disconnecting.",
                        live_connection_manager.heartbeat_timeout_seconds,
                        client_id,
                        stream_id,
                    )
                    try:
                        await websocket.close(
                            code=1008, reason="Heartbeat timeout exceeded"
                        )
                    except Exception as close_err:  # noqa: BLE001
                        logger.debug(
                            "Failed to cleanly close timed out websocket: %s", close_err
                        )
                    break
        except asyncio.CancelledError:
            pass

    monitor_task = asyncio.create_task(heartbeat_check_loop())

    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg: dict[str, Any] = json.loads(text)
            except json.JSONDecodeError:
                await live_connection_manager.send_json(
                    websocket, {"type": "error", "message": "Invalid JSON format"}
                )
                continue

            msg_type = msg.get("type")

            # Heartbeat ping handling
            if msg_type == "ping":
                live_connection_manager.record_heartbeat(client_id)
                await live_connection_manager.send_json(
                    websocket,
                    {
                        "type": "pong",
                        "client_timestamp": msg.get("timestamp"),
                        "server_time": datetime.now(UTC).isoformat(),
                    },
                )

            # Stream health check / metadata inquiry
            elif msg_type == "status":
                live_connection_manager.record_heartbeat(client_id)
                await live_connection_manager.send_json(
                    websocket,
                    {
                        "type": "status_response",
                        "stream_id": stream_id,
                        "viewer_count": live_connection_manager.get_stream_viewer_count(
                            stream_id
                        ),
                        "server_time": datetime.now(UTC).isoformat(),
                    },
                )

            # Broadcast chunk / segment notification to other stream viewers
            elif msg_type == "broadcast":
                live_connection_manager.record_heartbeat(client_id)
                broadcast_data = {
                    "type": "stream_update",
                    "stream_id": stream_id,
                    "sender": client_id,
                    "event": msg.get("event", "chunk"),
                    "payload": msg.get("payload", {}),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                await live_connection_manager.broadcast_to_stream(
                    stream_id, broadcast_data
                )

            else:
                live_connection_manager.record_heartbeat(client_id)
                await live_connection_manager.send_json(
                    websocket,
                    {
                        "type": "ack",
                        "received_type": msg_type,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally: client %s", client_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("WebSocket error for client %s: %s", client_id, exc)
    finally:
        monitor_task.cancel()
        live_connection_manager.disconnect(stream_id, client_id)

        # Notify Kafka if last viewer/broadcaster disconnected
        remaining = live_connection_manager.get_stream_viewer_count(stream_id)
        if remaining == 0:
            event_publisher.publish_live_event(
                stream_id=stream_id,
                event_type=VideoEventType.LIVE_STREAM_ENDED,
                status=EventStatus.COMPLETED,
                step="all_clients_disconnected",
                data={"stream_id": stream_id},
                flush_immediately=True,
            )


@router.get("/streams/{stream_id}/status")
async def get_stream_status(stream_id: str) -> dict[str, Any]:
    """Retrieve active viewer count and health status for a live stream."""
    count = live_connection_manager.get_stream_viewer_count(stream_id)
    return {
        "stream_id": stream_id,
        "active_viewers": count,
        "status": "live" if count > 0 else "offline",
        "timestamp": datetime.now(UTC).isoformat(),
    }
