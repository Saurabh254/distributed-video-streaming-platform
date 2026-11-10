import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.websocket.manager import LiveStreamConnectionManager


def test_live_connection_manager_heartbeat_lifecycle():
    mgr = LiveStreamConnectionManager(heartbeat_timeout_seconds=0.5)
    stream_id = f"stream-{uuid4()}"
    client_id = f"client-{uuid4()}"

    mgr._streams[stream_id] = {client_id: None}  # type: ignore
    mgr._last_heartbeat[client_id] = time.time()

    assert mgr.is_alive(client_id) is True
    assert mgr.get_stream_viewer_count(stream_id) == 1

    # Simulate timeout
    mgr._last_heartbeat[client_id] = time.time() - 1.0
    assert mgr.is_alive(client_id) is False

    # Disconnect
    mgr.disconnect(stream_id, client_id)
    assert mgr.get_stream_viewer_count(stream_id) == 0


def test_live_websocket_connection_and_heartbeat_ping_pong(client: TestClient):
    stream_id = f"stream-{uuid4().hex[:8]}"

    with client.websocket_connect(f"/api/v1/live/ws/{stream_id}") as ws:
        # 1. Receive handshake greeting
        greeting_raw = ws.receive_text()
        greeting = json.loads(greeting_raw)
        assert greeting["type"] == "connection_established"
        assert greeting["stream_id"] == stream_id
        assert "heartbeat_interval_seconds" in greeting
        client_id = greeting["client_id"]
        assert client_id.startswith("client-")

        # 2. Send ping with timestamp
        test_ts = int(time.time() * 1000)
        ws.send_text(json.dumps({"type": "ping", "timestamp": test_ts}))

        # 3. Receive pong
        pong_raw = ws.receive_text()
        pong = json.loads(pong_raw)
        assert pong["type"] == "pong"
        assert pong["client_timestamp"] == test_ts
        assert "server_time" in pong

        # 4. Status query
        ws.send_text(json.dumps({"type": "status"}))
        status_raw = ws.receive_text()
        status_msg = json.loads(status_raw)
        assert status_msg["type"] == "status_response"
        assert status_msg["viewer_count"] >= 1

        # 5. Broadcast message
        ws.send_text(
            json.dumps(
                {
                    "type": "broadcast",
                    "event": "chunk_available",
                    "payload": {"chunk_id": 1, "bitrate": "1500k"},
                }
            )
        )


def test_live_stream_http_status_endpoint(client: TestClient):
    stream_id = f"stream-{uuid4().hex[:8]}"
    res = client.get(f"/api/v1/live/streams/{stream_id}/status")
    assert res.status_code == 200
    data = res.json()
    assert data["stream_id"] == stream_id
    assert "active_viewers" in data
    assert data["status"] in ("live", "offline")
