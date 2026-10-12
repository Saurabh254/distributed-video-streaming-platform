from datetime import UTC, datetime
from typing import Any

import jwt
from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.core.security import (
    block_access_token,
    create_access_token,
    create_refresh_token,
    decode_jwt,
    generate_salt,
    hash_password,
    is_refresh_token_valid,
    revoke_all_user_refresh_tokens,
    revoke_refresh_token,
    store_refresh_token,
    verify_password,
)
from app.repository.auth import AuthRepository
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)


class AuthService:
    """Business logic for user registration, authentication, JWT token refresh, and logout."""

    def __init__(self, repo: AuthRepository, redis: Redis) -> None:
        self._repo = repo
        self._redis = redis

    async def register(
        self, req: UserRegisterRequest
    ) -> tuple[dict[str, Any], TokenResponse]:
        """Register a new user, storing password hash and salt in separate tables."""
        if await self._repo.is_username_taken(req.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken",
            )

        if await self._repo.is_email_taken(req.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        salt = generate_salt(nbytes=16)
        password_hash = hash_password(req.password, salt)

        user = await self._repo.create_user_with_password(
            username=req.username,
            email=req.email,
            password_hash=password_hash,
            salt=salt,
        )

        access_token, _, access_exp = create_access_token(
            user_id=str(user["id"]),
            username=user["username"],
            email=user["email"],
        )
        refresh_token, refresh_jti, refresh_exp = create_refresh_token(
            user_id=str(user["id"])
        )

        await store_refresh_token(
            self._redis,
            user_id=str(user["id"]),
            jti=refresh_jti,
            ttl_seconds=refresh_exp,
        )

        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=access_exp,
        )

        return user, tokens

    async def login(
        self, req: UserLoginRequest
    ) -> tuple[dict[str, Any], TokenResponse]:
        """Authenticate user by identifier and password, returning access and refresh JWTs."""
        user = await self._repo.get_user_by_identifier(req.identifier)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password",
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        creds = await self._repo.get_password_credentials(user["id"])
        if not creds:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password",
            )

        is_valid = verify_password(
            password=req.password,
            salt=creds["salt"],
            password_hash=creds["password_hash"],
            iterations=creds["iterations"],
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password",
            )

        access_token, _, access_exp = create_access_token(
            user_id=str(user["id"]),
            username=user["username"],
            email=user["email"],
        )
        refresh_token, refresh_jti, refresh_exp = create_refresh_token(
            user_id=str(user["id"])
        )

        await store_refresh_token(
            self._redis,
            user_id=str(user["id"]),
            jti=refresh_jti,
            ttl_seconds=refresh_exp,
        )

        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=access_exp,
        )

        return user, tokens

    async def refresh(self, refresh_token_str: str) -> TokenResponse:
        """Validate refresh token, rotate tokens, and update Redis session."""
        try:
            payload = decode_jwt(refresh_token_str)
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            ) from exc

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        jti = payload.get("jti")
        if not user_id or not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed token payload",
            )

        # Verify refresh token session in Redis
        is_active = await is_refresh_token_valid(self._redis, user_id, jti)
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or expired",
            )

        # Rotate: revoke current refresh token
        await revoke_refresh_token(self._redis, user_id, jti)

        user = await self._repo.get_user_by_id(user_id)
        if not user or not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or account deactivated",
            )

        # Issue new token pair
        access_token, _, access_exp = create_access_token(
            user_id=str(user["id"]),
            username=user["username"],
            email=user["email"],
        )
        new_refresh_token, new_refresh_jti, new_refresh_exp = create_refresh_token(
            user_id=str(user["id"])
        )

        await store_refresh_token(
            self._redis,
            user_id=str(user["id"]),
            jti=new_refresh_jti,
            ttl_seconds=new_refresh_exp,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=access_exp,
        )

    async def logout(
        self,
        user_id: str,
        refresh_token_str: str | None = None,
        access_token_str: str | None = None,
    ) -> None:
        """Revoke refresh token and blacklist access token in Redis."""
        # 1. Revoke specific refresh token if supplied, otherwise revoke all for user
        if refresh_token_str:
            try:
                payload = decode_jwt(refresh_token_str)
                if payload.get("type") == "refresh":
                    token_user = payload.get("sub")
                    token_jti = payload.get("jti")
                    if token_user and token_jti:
                        await revoke_refresh_token(self._redis, token_user, token_jti)
            except jwt.PyJWTError:
                pass
        else:
            await revoke_all_user_refresh_tokens(self._redis, user_id)

        # 2. Blacklist access token until expiration
        if access_token_str:
            try:
                payload = decode_jwt(access_token_str)
                if payload.get("type") == "access":
                    jti = payload.get("jti")
                    exp = payload.get("exp", 0)
                    now_ts = int(datetime.now(UTC).timestamp())
                    remaining = exp - now_ts
                    if jti and remaining > 0:
                        await block_access_token(self._redis, jti, remaining)
            except jwt.PyJWTError:
                pass
