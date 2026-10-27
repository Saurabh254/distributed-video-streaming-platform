import json
import logging
from datetime import UTC, datetime

import redis

from app.core.config import settings
from app.workers.celery_app import app

logger = logging.getLogger(__name__)

# Redis client for DB 1
redis_client = redis.Redis(
    host=settings.redis_dsn.host or "localhost",
    port=settings.redis_dsn.port or 6379,
    password=settings.redis_dsn.password,
    db=1,
    decode_responses=True,
)


@app.task(name="app.workers.tasks.dead_letter.record_dead_letter")
def record_dead_letter(
    original_task,
    task_id,
    args,
    kwargs,
    error,
    traceback=None,
):
    dlq_record = {
        "task": original_task,
        "task_id": task_id,
        "args": args,
        "kwargs": kwargs,
        "error": error,
        "traceback": traceback,
        "failed_at": datetime.now(UTC).isoformat(),
    }
    payload = json.dumps(dlq_record)

    # 1. Queue list for DLQ inspection and replay
    redis_client.lpush("dlq:video_tasks", payload)

    # 2. Hash keyed by task_id for deduplication and lookup
    redis_client.hset("dlq:video_tasks:by_id", task_id, payload)

    logger.warning(
        "Recorded DLQ task to Redis DB 1 [dlq:video_tasks]: task=%s, task_id=%s, error=%s",
        original_task,
        task_id,
        error,
    )
