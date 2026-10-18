import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, Retries, TimeLimit

from app.core.config import settings


def setup_broker() -> RedisBroker:
    """Initialize and configure Dramatiq Redis broker with production middleware."""
    redis_broker = RedisBroker(url=str(settings.redis_dsn))
    redis_broker.add_middleware(AgeLimit(max_age=3600_000))  # 1 hour
    redis_broker.add_middleware(TimeLimit(time_limit=300_000))  # 5 minutes
    redis_broker.add_middleware(Retries(max_retries=3))
    dramatiq.set_broker(redis_broker)
    return redis_broker


broker = setup_broker()
