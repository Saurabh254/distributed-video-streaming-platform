from collections.abc import AsyncIterator
from typing import Annotated, Any

import jwt
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager
from app.core.connectors.s3 import S3Manager, s3_manager
from app.core.logging import set_user_id
from app.core.security import decode_jwt, is_access_token_blocked
from app.repository.video import VideoRepository
from app.services.upload_service import UploadService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_db_connection() -> AsyncIterator[AsyncConnection]:
    """Dependency borrowing a PostgreSQL connection from the pool."""
    async with db_manager.get_connection() as conn:
        yield conn


def get_db_pool() -> AsyncConnectionPool:
    return db_manager.get_pool()


DbConnDep = Annotated[AsyncConnection, Depends(get_db_connection)]
DbDep = DbConnDep
DbPoolDep = Annotated[AsyncConnectionPool, Depends(get_db_pool)]

RedisDep = Annotated[aioredis.Redis, Depends(redis_manager.get_client)]


def get_s3_manager() -> S3Manager:
    return s3_manager


S3Dep = Annotated[S3Manager, Depends(get_s3_manager)]


def get_video_repo(conn: DbDep) -> VideoRepository:
    return VideoRepository(conn)


VideoRepoDep = Annotated[VideoRepository, Depends(get_video_repo)]


def get_upload_service(repo: VideoRepoDep, s3: S3Dep, redis: RedisDep) -> UploadService:
    return UploadService(repo=repo, s3=s3, redis=redis)


UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    redis_conn: RedisDep,
) -> dict[str, Any]:
    """Validate Bearer JWT token against signature, expiry, and Redis revocation list."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_jwt(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    if jti and await is_access_token_blocked(redis_conn, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    set_user_id(str(user_id))
    return {
        "id": user_id,
        "username": payload.get("username", ""),
        "email": payload.get("email", ""),
    }


CurrentUserDep = Annotated[dict[str, Any], Depends(get_current_user)]

__all__ = [
    "CurrentUserDep",
    "DbConnDep",
    "DbDep",
    "DbPoolDep",
    "RedisDep",
    "S3Dep",
    "UploadServiceDep",
    "VideoRepoDep",
    "get_current_user",
    "get_db_connection",
    "get_db_pool",
    "get_s3_manager",
    "get_upload_service",
    "get_video_repo",
    "oauth2_scheme",
]
