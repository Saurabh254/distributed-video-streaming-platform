import logging
from typing import Any

from confluent_kafka import Producer

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaManager:
    """Manages the Confluent Kafka Producer lifecycle and delivery mechanisms."""

    def __init__(self, bootstrap_servers: str | None = None) -> None:
        self._producer: Producer | None = None
        self._bootstrap_servers = bootstrap_servers

    @property
    def bootstrap_servers(self) -> str:
        return self._bootstrap_servers or settings.kafka_bootstrap_servers

    def start(self) -> None:
        """Initialize the Kafka Producer with robust delivery semantics."""
        if self._producer is not None:
            return

        conf: dict[str, Any] = {
            "bootstrap.servers": self.bootstrap_servers,
            "enable.idempotence": True,
            "acks": "all",
            "retries": 5,
            "retry.backoff.ms": 250,
            "max.in.flight.requests.per.connection": 5,
            "linger.ms": 10,
        }

        try:
            self._producer = Producer(conf)
            logger.info(
                "Connected to Kafka broker at %s",
                self.bootstrap_servers,
            )
        except Exception:
            logger.exception(
                "Failed to initialize Kafka producer at %s", self.bootstrap_servers
            )
            raise

    def get_producer(self) -> Producer:
        """Return the active Producer instance, auto-starting if necessary."""
        if self._producer is None:
            self.start()
        assert self._producer is not None
        return self._producer

    def validate_connection(self, timeout: float = 5.0) -> bool:
        """Validate connection by querying cluster metadata."""
        try:
            prod = self.get_producer()
            metadata = prod.list_topics(timeout=timeout)
            return metadata is not None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kafka healthcheck validation failed: %s", exc)
            return False

    def flush(self, timeout: float | None = None) -> int:
        """Flush outstanding messages within timeout seconds. Returns remaining messages."""
        if self._producer is None:
            return 0
        t = timeout if timeout is not None else settings.kafka_flush_timeout_seconds
        remaining = self._producer.flush(timeout=t)
        if remaining > 0:
            logger.warning(
                "%d Kafka message(s) still pending after %.1fs flush", remaining, t
            )
        return remaining

    def poll(self, timeout: float = 0.0) -> int:
        """Poll for delivery callbacks."""
        if self._producer is None:
            return 0
        return self._producer.poll(timeout)

    def close(self) -> None:
        """Flush pending messages and release producer resources."""
        if self._producer is not None:
            self.flush(timeout=settings.kafka_flush_timeout_seconds)
            self._producer = None
            logger.info("Kafka producer closed")


kafka_manager = KafkaManager()
