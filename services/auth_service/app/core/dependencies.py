from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends

from services.auth_service.app.core.connectors.redis import redis_manager

RedisDep = Annotated[aioredis.Redis, Depends(redis_manager.get_client)]
