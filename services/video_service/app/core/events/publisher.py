import logging
from typing import Any

from confluent_kafka import KafkaError, Message

from app.core.config import settings
from app.core.connectors.kafka import KafkaManager, kafka_manager
from app.schemas.events import (
    EventStatus,
    StreamType,
    VideoEventType,
    VideoProcessingEvent,
)

logger = logging.getLogger(__name__)


def _delivery_report(err: KafkaError | None, msg: Message) -> None:
    """Callback invoked once by produce() or poll() after delivery attempt."""
    if err is not None:
        logger.error(
            "Kafka delivery failed for topic=%s, key=%s: %s",
            msg.topic(),
            msg.key(),
            err,
        )
    else:
        logger.debug(
            "Kafka message delivered to topic=%s, partition=%d, offset=%d",
            msg.topic(),
            msg.partition(),
            msg.offset(),
        )


class VideoEventPublisher:
    """
    Unified Kafka Event Publisher for VOD and Live Streaming media processing.

    Ensures partition affinity by pinning the message key to `entity_id`
    (video_id for VOD, stream_id for Live Streaming) so that downstream
    SSE/WebSocket consumer endpoints deliver sequentially ordered updates.
    """

    def __init__(
        self,
        manager: KafkaManager | None = None,
        default_topic: str | None = None,
        enable_redis_pubsub: bool = True,
    ) -> None:
        self._manager = manager or kafka_manager
        self._default_topic = default_topic
        self._enable_redis_pubsub = enable_redis_pubsub
        self._redis: Any = None

    def _get_redis(self) -> Any:
        if self._redis is None and self._enable_redis_pubsub:
            try:
                import redis

                self._redis = redis.Redis.from_url(
                    str(settings.redis_dsn), decode_responses=True
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not connect to Redis for event pub/sub: %s", exc)
                self._redis = None
        return self._redis

    @property
    def default_topic(self) -> str:
        return self._default_topic or settings.kafka_events_topic

    def publish(
        self,
        event: VideoProcessingEvent,
        topic: str | None = None,
        flush_immediately: bool = False,
    ) -> bool:
        """
        Publish a validated VideoProcessingEvent to Kafka.
        Uses event.entity_id as the message key to preserve causal ordering per entity.
        """
        target_topic = topic or self.default_topic
        key = str(event.entity_id).encode("utf-8")
        payload = event.model_dump_json().encode("utf-8")

        try:
            prod = self._manager.get_producer()
            prod.produce(
                topic=target_topic,
                key=key,
                value=payload,
                on_delivery=_delivery_report,
            )
            # Service delivery callbacks non-blockingly
            prod.poll(0)

            # Dual-publish to Redis Pub/Sub channel for instantaneous SSE / WS forwarding
            try:
                r = self._get_redis()
                if r is not None:
                    r.publish(
                        f"events:video:{event.entity_id}", payload.decode("utf-8")
                    )
            except Exception as redis_exc:  # noqa: BLE001
                logger.debug("Redis pub/sub broadcast notice: %s", redis_exc)

            # Terminal states (completed/failed) or explicit requests flush immediately
            is_terminal = event.status in (
                EventStatus.COMPLETED,
                EventStatus.READY,
                EventStatus.FAILED,
            ) or event.event_type in (
                VideoEventType.VOD_COMPLETED,
                VideoEventType.VOD_FAILED,
                VideoEventType.LIVE_STREAM_ENDED,
                VideoEventType.LIVE_STREAM_FAILED,
                VideoEventType.TASK_SUCCEEDED,
                VideoEventType.TASK_FAILED,
            )

            if flush_immediately or is_terminal:
                self.flush()

            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to produce video event [type=%s, entity=%s]: %s",
                event.event_type,
                event.entity_id,
                exc,
            )
            return False

    def publish_vod_event(
        self,
        video_id: str,
        event_type: str | VideoEventType,
        status: str | EventStatus = EventStatus.PROCESSING,
        step: str | None = None,
        progress: float | None = None,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        topic: str | None = None,
        flush_immediately: bool = False,
    ) -> bool:
        """Convenience method for publishing VOD lifecycle and progress events."""
        ev_type = (
            event_type.value
            if isinstance(event_type, VideoEventType)
            else str(event_type)
        )
        ev_status = EventStatus(status) if isinstance(status, str) else status

        event = VideoProcessingEvent(
            event_type=ev_type,
            entity_id=str(video_id),
            stream_type=StreamType.VOD,
            status=ev_status,
            step=step,
            progress=progress,
            data=data or {},
            error=error,
        )
        target_topic = topic or settings.kafka_vod_events_topic
        return self.publish(
            event, topic=target_topic, flush_immediately=flush_immediately
        )

    def publish_live_event(
        self,
        stream_id: str,
        event_type: str | VideoEventType,
        status: str | EventStatus = EventStatus.PROCESSING,
        step: str | None = None,
        progress: float | None = None,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        topic: str | None = None,
        flush_immediately: bool = False,
    ) -> bool:
        """Convenience method for publishing Live Streaming events (chunks, segments, state)."""
        ev_type = (
            event_type.value
            if isinstance(event_type, VideoEventType)
            else str(event_type)
        )
        ev_status = EventStatus(status) if isinstance(status, str) else status

        event = VideoProcessingEvent(
            event_type=ev_type,
            entity_id=str(stream_id),
            stream_type=StreamType.LIVE,
            status=ev_status,
            step=step,
            progress=progress,
            data=data or {},
            error=error,
        )
        target_topic = topic or settings.kafka_live_events_topic
        return self.publish(
            event, topic=target_topic, flush_immediately=flush_immediately
        )

    def flush(self, timeout: float | None = None) -> int:
        """Flush any pending messages to Kafka."""
        return self._manager.flush(timeout=timeout)


event_publisher = VideoEventPublisher()
