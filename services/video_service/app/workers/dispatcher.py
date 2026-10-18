import asyncio
import logging
import os
import signal
import sys
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import settings
from app.workers.actors import process_video_thumbnail, transcode_video_hls

logger = logging.getLogger(__name__)

STREAM_NAME = "stream:video:events"
CONSUMER_GROUP = "video-processors"
CONSUMER_NAME = f"dispatcher-{os.getpid()}"


class StreamDispatcher:
    """
    Consumes events from Redis Stream using Consumer Groups and dispatches
    tasks to Dramatiq background workers.
    """

    def __init__(self, redis_client: Redis | None = None) -> None:
        self._redis = redis_client
        self._own_client = False
        self._stop_event = asyncio.Event()

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(str(settings.redis_dsn), decode_responses=True)
            self._own_client = True
        return self._redis

    async def init_stream_group(self, redis: Redis) -> None:
        """Ensure Redis stream and consumer group exist."""
        try:
            await redis.xgroup_create(
                name=STREAM_NAME,
                groupname=CONSUMER_GROUP,
                id="0",
                mkstream=True,
            )
            logger.info(
                "Created Redis stream '%s' with consumer group '%s'",
                STREAM_NAME,
                CONSUMER_GROUP,
            )
        except ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                # Group already exists
                pass
            else:
                logger.error("Error creating consumer group: %s", exc)
                raise

    async def process_message(self, message_id: str, data: dict[str, Any]) -> None:
        """Handle individual stream event and dispatch to Dramatiq."""
        event = data.get("event")
        if event == "video.uploaded":
            video_id = data.get("video_id")
            s3_bucket = data.get("s3_bucket")
            s3_key = data.get("s3_key")

            if video_id and s3_bucket and s3_key:
                logger.info(
                    "Dispatching video_id=%s to Dramatiq thumbnail and HLS processors",
                    video_id,
                )
                process_video_thumbnail.send(
                    video_id=video_id,
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                )
                transcode_video_hls.send(
                    video_id=video_id,
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                )
            else:
                logger.warning(
                    "Malformed video.uploaded stream message %s: %s",
                    message_id,
                    data,
                )

    async def run(self) -> None:
        """Main consumer loop."""
        redis = await self._get_redis()
        await self.init_stream_group(redis)

        logger.info(
            "Redis Stream Dispatcher started listening on '%s' (group: '%s', consumer: '%s')",
            STREAM_NAME,
            CONSUMER_GROUP,
            CONSUMER_NAME,
        )

        while not self._stop_event.is_set():
            try:
                # Read new messages for this consumer group
                streams_data = await redis.xreadgroup(
                    groupname=CONSUMER_GROUP,
                    consumername=CONSUMER_NAME,
                    streams={STREAM_NAME: ">"},
                    count=10,
                    block=1000,  # Block 1s
                )

                if not streams_data:
                    await asyncio.sleep(0.1)
                    continue

                for stream_name, messages in streams_data:
                    for msg_id, data in messages:
                        try:
                            await self.process_message(msg_id, data)
                            # Acknowledge receipt and dispatch
                            await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
                        except Exception:
                            logger.exception(
                                "Failed processing stream message %s",
                                msg_id,
                            )

            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error in Redis stream consumer loop: %s", exc)
                await asyncio.sleep(1.0)

        logger.info("Redis Stream Dispatcher stopped.")
        if self._own_client and self._redis:
            await self._redis.aclose()

    def stop(self) -> None:
        """Signal dispatcher loop to terminate."""
        self._stop_event.set()


async def run_standalone_dispatcher() -> None:
    dispatcher = StreamDispatcher()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, dispatcher.stop)
        except NotImplementedError:
            pass

    await dispatcher.run()


if __name__ == "__main__":
    from app.workers.actors import setup_worker_logging

    logging.basicConfig(level=logging.INFO)
    setup_worker_logging("video_dispatcher")
    try:
        asyncio.run(run_standalone_dispatcher())
    except KeyboardInterrupt:
        sys.exit(0)
