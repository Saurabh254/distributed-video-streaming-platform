from typing import Any

import jwt
from redis.asyncio import Redis

from app.core.config import settings


def decode_jwt(token: str) -> dict[str, Any]:
    """Decode and verify JWT signature and expiration using the shared secret key."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


async def is_access_token_blocked(redis: Redis, jti: str) -> bool:
    """Check if an access token JTI is blacklisted in Redis."""
    key = f"auth:blacklist:{jti}"
    return bool(await redis.exists(key))
