from collections.abc import AsyncIterator
from typing import Annotated, Any

import jwt
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.core.connectors.postgres import db_manager
from app.core.connectors.redis import redis_manager
from app.core.logging import set_user_id
from app.core.security import decode_jwt, is_access_token_blocked
from app.repository.auth import AuthRepository
from app.schemas.auth import UserLoginRequest
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

RedisDep = Annotated[aioredis.Redis, Depends(redis_manager.get_client)]


async def get_db_connection() -> AsyncIterator[AsyncConnection]:
    """Dependency that borrows a PostgreSQL connection from the pool for a request and releases it upon completion."""
    async with db_manager.get_connection() as conn:
        yield conn


def get_db_pool() -> AsyncConnectionPool:
    """Dependency that provides the PostgreSQL connection pool instance."""
    return db_manager.get_pool()


DbConnDep = Annotated[AsyncConnection, Depends(get_db_connection)]
DbDep = DbConnDep
PgDep = DbConnDep
DbPoolDep = Annotated[AsyncConnectionPool, Depends(get_db_pool)]
PgPoolDep = DbPoolDep


def get_auth_repo(conn: DbDep) -> AuthRepository:
    """Dependency providing AuthRepository instance."""
    return AuthRepository(conn)


AuthRepoDep = Annotated[AuthRepository, Depends(get_auth_repo)]


def get_auth_service(repo: AuthRepoDep, redis: RedisDep) -> AuthService:
    """Dependency providing AuthService instance."""
    return AuthService(repo=repo, redis=redis)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def parse_login_credentials(request: Request) -> UserLoginRequest:
    """Parse login credentials from either JSON body or OAuth2 form-data."""
    content_type = request.headers.get("content-type", "")
    if (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
    ):
        form = await request.form()
        identifier = form.get("username") or form.get("identifier") or form.get("email")
        password = form.get("password")
        if not identifier or not password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing identifier/username or password",
            )
        return UserLoginRequest(identifier=str(identifier), password=str(password))
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON payload",
        ) from exc
    return UserLoginRequest.model_validate(body)


LoginCredentialsDep = Annotated[UserLoginRequest, Depends(parse_login_credentials)]


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db_conn: DbDep,
    redis_conn: RedisDep,
) -> dict[str, Any]:
    """Dependency that validates Bearer JWT token against signature and Redis blacklist, returning the authenticated user."""
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

    user_id = str(payload.get("sub"))
    repo = AuthRepository(db_conn)
    user = await repo.get_user_by_id(user_id)
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    set_user_id(str(user_id))
    return user


CurrentUserDep = Annotated[dict[str, Any], Depends(get_current_user)]

__all__ = [
    "AuthRepoDep",
    "AuthServiceDep",
    "CurrentUserDep",
    "DbConnDep",
    "DbDep",
    "DbPoolDep",
    "LoginCredentialsDep",
    "PgDep",
    "PgPoolDep",
    "RedisDep",
    "get_auth_repo",
    "get_auth_service",
    "get_current_user",
    "get_db_connection",
    "get_db_pool",
    "oauth2_scheme",
    "parse_login_credentials",
]
