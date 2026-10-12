import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from redis.asyncio import Redis

from app.core.config import settings


def generate_salt(nbytes: int = 16) -> str:
    """Generate a cryptographically secure random salt in hex representation."""
    return secrets.token_hex(nbytes)


def hash_password(password: str, salt: str, iterations: int = 600_000) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and the provided salt."""
    salt_bytes = bytes.fromhex(salt)
    key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=password.encode("utf-8"),
        salt=salt_bytes,
        iterations=iterations,
    )
    return key.hex()


def verify_password(
    password: str,
    salt: str,
    password_hash: str,
    iterations: int = 600_000,
) -> bool:
    """Verify a plain password against the stored salt and hash using constant-time comparison."""
    computed_hash = hash_password(password, salt, iterations)
    return secrets.compare_digest(computed_hash, password_hash)


def create_access_token(
    user_id: str,
    username: str,
    email: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, int]:
    """
    Generate a signed JWT access token.
    Returns: (token, jti, expires_in_seconds)
    """
    now = datetime.now(UTC)
    delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    exp = now + delta
    jti = str(uuid4())

    payload = {
        "sub": str(user_id),
        "username": username,
        "email": email,
        "type": "access",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, jti, int(delta.total_seconds())


def create_refresh_token(
    user_id: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, int]:
    """
    Generate a signed JWT refresh token.
    Returns: (token, jti, expires_in_seconds)
    """
    now = datetime.now(UTC)
    delta = expires_delta or timedelta(days=settings.refresh_token_expire_days)
    exp = now + delta
    jti = str(uuid4())

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, jti, int(delta.total_seconds())


def decode_jwt(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token signature and expiration."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


async def store_refresh_token(
    redis: Redis, user_id: str, jti: str, ttl_seconds: int
) -> None:
    """Store an active refresh token session in Redis."""
    key = f"auth:refresh:{user_id}:{jti}"
    await redis.set(key, "active", ex=ttl_seconds)


async def is_refresh_token_valid(redis: Redis, user_id: str, jti: str) -> bool:
    """Check if the refresh token is present and active in Redis."""
    key = f"auth:refresh:{user_id}:{jti}"
    return bool(await redis.exists(key))


async def revoke_refresh_token(redis: Redis, user_id: str, jti: str) -> None:
    """Revoke a specific refresh token from Redis."""
    key = f"auth:refresh:{user_id}:{jti}"
    await redis.delete(key)


async def revoke_all_user_refresh_tokens(redis: Redis, user_id: str) -> None:
    """Revoke all refresh tokens for a user (logout all sessions)."""
    pattern = f"auth:refresh:{user_id}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)


async def block_access_token(
    redis: Redis, jti: str, remaining_ttl_seconds: int
) -> None:
    """Blacklist an access token in Redis until its natural expiration."""
    if remaining_ttl_seconds > 0:
        key = f"auth:blacklist:{jti}"
        await redis.set(key, "revoked", ex=remaining_ttl_seconds)


async def is_access_token_blocked(redis: Redis, jti: str) -> bool:
    """Check if an access token JTI is blacklisted in Redis."""
    key = f"auth:blacklist:{jti}"
    return bool(await redis.exists(key))
