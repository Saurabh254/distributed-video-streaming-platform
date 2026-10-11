from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from src.core.connectors.redis import redis_manager

RedisDep = Annotated[aioredis.Redis, Depends(redis_manager.get_client)]
