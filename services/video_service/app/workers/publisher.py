import json

from confluent_kafka import Producer

producer = None


def get_producer():
    global producer

    if producer is None:
        producer = Producer(
            {
                "bootstrap.servers": "127.0.0.1:9092",
                "enable.idempotence": True,
                "acks": "all",
            }
        )
    return producer


def publish_event(event: str, task_id: str | None, **data):
    payload = {
        "event": event,
        "task_id": task_id,
        "data": data,
    }
    producer = get_producer()

    producer.produce(
        topic="video-task-events",
        key=task_id,
        value=json.dumps(payload, default=str),
    )

    # Wait for delivery confirmation.
    remaining = producer.flush(timeout=10)

    if remaining:
        raise RuntimeError(f"{remaining} Kafka message(s) still pending delivery")
