import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.events.publisher import VideoEventPublisher
from app.schemas.events import (
    EventStatus,
    StreamType,
    VideoEventType,
    VideoProcessingEvent,
)
from app.workers.publisher import publish_event


def test_video_processing_event_schema():
    video_id = str(uuid4())
    event = VideoProcessingEvent(
        event_type=VideoEventType.VOD_TRANSCODING_PROGRESS,
        entity_id=video_id,
        stream_type=StreamType.VOD,
        status=EventStatus.PROCESSING,
        step="transcoding_hls",
        progress=45.5,
        data={"resolution": "720p", "fps": 30},
    )

    data = event.model_dump()
    assert data["event_type"] == "video.vod.transcoding_progress"
    assert data["entity_id"] == video_id
    assert data["stream_type"] == "vod"
    assert data["status"] == "processing"
    assert data["progress"] == 45.5
    assert data["data"]["resolution"] == "720p"

    json_str = event.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["entity_id"] == video_id
    assert "event_id" in parsed
    assert "timestamp" in parsed


def test_publisher_vod_event_produces_to_kafka():
    mock_producer = MagicMock()
    mock_manager = MagicMock()
    mock_manager.get_producer.return_value = mock_producer

    publisher = VideoEventPublisher(manager=mock_manager, default_topic="test-events")
    video_id = str(uuid4())

    success = publisher.publish_vod_event(
        video_id=video_id,
        event_type=VideoEventType.VOD_PROCESSING_STARTED,
        status=EventStatus.PROCESSING,
        step="probing_metadata",
        data={"format": "mp4"},
    )

    assert success is True
    mock_manager.get_producer.assert_called_once()
    mock_producer.produce.assert_called_once()

    call_kwargs = mock_producer.produce.call_args.kwargs
    assert call_kwargs["topic"] == "video-task-events"
    assert call_kwargs["key"] == video_id.encode("utf-8")

    payload = json.loads(call_kwargs["value"].decode("utf-8"))
    assert payload["entity_id"] == video_id
    assert payload["stream_type"] == "vod"
    assert payload["event_type"] == VideoEventType.VOD_PROCESSING_STARTED.value
    assert payload["status"] == "processing"
    assert payload["step"] == "probing_metadata"
    assert payload["data"]["format"] == "mp4"


def test_publisher_live_event_produces_to_kafka():
    mock_producer = MagicMock()
    mock_manager = MagicMock()
    mock_manager.get_producer.return_value = mock_producer

    publisher = VideoEventPublisher(manager=mock_manager, default_topic="test-events")
    stream_id = f"stream-{uuid4()}"

    success = publisher.publish_live_event(
        stream_id=stream_id,
        event_type=VideoEventType.LIVE_STREAM_SEGMENT_READY,
        status=EventStatus.PROCESSING,
        step="segment_001.ts",
        progress=100.0,
        data={"duration": 4.0, "sequence": 1},
    )

    assert success is True
    mock_producer.produce.assert_called_once()

    call_kwargs = mock_producer.produce.call_args.kwargs
    assert call_kwargs["topic"] == "video-task-events"
    assert call_kwargs["key"] == stream_id.encode("utf-8")

    payload = json.loads(call_kwargs["value"].decode("utf-8"))
    assert payload["entity_id"] == stream_id
    assert payload["stream_type"] == "live"
    assert payload["event_type"] == VideoEventType.LIVE_STREAM_SEGMENT_READY.value
    assert payload["data"]["sequence"] == 1


def test_publisher_terminal_event_triggers_flush():
    mock_producer = MagicMock()
    mock_manager = MagicMock()
    mock_manager.get_producer.return_value = mock_producer

    publisher = VideoEventPublisher(manager=mock_manager, default_topic="test-events")
    video_id = str(uuid4())

    # Completed event should flush
    publisher.publish_vod_event(
        video_id=video_id,
        event_type=VideoEventType.VOD_COMPLETED,
        status=EventStatus.COMPLETED,
        step="completed",
        data={"url": "http://example.com/master.m3u8"},
    )

    mock_manager.flush.assert_called_once()


def test_backward_compatible_publish_event():
    mock_producer = MagicMock()
    mock_manager = MagicMock()
    mock_manager.get_producer.return_value = mock_producer

    from app.core.events.publisher import event_publisher

    original_manager = event_publisher._manager
    event_publisher._manager = mock_manager

    try:
        task_id = str(uuid4())
        video_id = str(uuid4())

        publish_event(
            event="task.started",
            task_id=task_id,
            args=[video_id],
            kwargs={},
        )

        mock_producer.produce.assert_called_once()
        call_kwargs = mock_producer.produce.call_args.kwargs
        assert call_kwargs["key"] == video_id.encode("utf-8")

        payload = json.loads(call_kwargs["value"].decode("utf-8"))
        assert payload["entity_id"] == video_id
        assert payload["event_type"] == "task.started"
        assert payload["status"] == "processing"
    finally:
        event_publisher._manager = original_manager


def test_real_kafka_event_publishing():
    """Integration test verifying real event publishing against running Kafka broker."""
    from app.core.connectors.kafka import kafka_manager
    from app.core.events.publisher import event_publisher

    # Only run if Kafka broker is reachable
    if not kafka_manager.validate_connection(timeout=2.0):
        pytest.skip("Kafka broker not available in this test environment")

    video_id = str(uuid4())
    success = event_publisher.publish_vod_event(
        video_id=video_id,
        event_type=VideoEventType.VOD_PROBING,
        status=EventStatus.PROCESSING,
        step="probing",
        data={"integration_test": True},
        flush_immediately=True,
    )
    assert success is True
