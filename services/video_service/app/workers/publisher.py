import logging
from typing import Any

from confluent_kafka import Producer

from app.core.connectors.kafka import kafka_manager
from app.core.events.publisher import VideoEventPublisher, event_publisher
from app.schemas.events import EventStatus, StreamType, VideoProcessingEvent

logger = logging.getLogger(__name__)


def get_producer() -> Producer:
    """Backward-compatible access to the underlying confluent_kafka Producer."""
    return kafka_manager.get_producer()


def publish_event(event: str, task_id: str | None, **data: Any) -> bool:
    """
    Backward-compatible task event publisher used by BaseTask lifecycle.
    Routes through the unified VideoEventPublisher.
    """
    status_map = {
        "task.started": EventStatus.PROCESSING,
        "task.retrying": EventStatus.PROCESSING,
        "task.succeeded": EventStatus.COMPLETED,
        "task.failed": EventStatus.FAILED,
    }
    status = status_map.get(event, EventStatus.PROCESSING)
    err = str(data.get("error")) if "error" in data else None

    # Resolve entity_id from task args or kwargs if available
    args = data.get("args") or ()
    kwargs = data.get("kwargs") or {}
    entity_id = kwargs.get("video_id") or kwargs.get("stream_id")
    if not entity_id and args and isinstance(args, (list, tuple)) and len(args) > 0:
        entity_id = str(args[0])
    if not entity_id:
        entity_id = str(task_id or "system")

    evt = VideoProcessingEvent(
        event_type=event,
        entity_id=str(entity_id),
        stream_type=StreamType.VOD,
        status=status,
        step=event,
        data={"task_id": task_id, **data},
        error=err,
    )
    return event_publisher.publish(evt)


__all__ = ["VideoEventPublisher", "event_publisher", "get_producer", "publish_event"]
