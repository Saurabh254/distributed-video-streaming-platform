from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    AuthServiceDep,
    CurrentUserDep,
    LoginCredentialsDep,
    oauth2_scheme,
)
from app.schemas.auth import (
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    req: UserRegisterRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Register a new user and generate access & refresh tokens."""
    user, tokens = await auth_service.register(req)
    tokens.user = UserResponse.model_validate(user)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/UserLoginRequest"}
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {
                                "type": "string",
                                "description": "Username or email (OAuth2 compatible)",
                            },
                            "password": {
                                "type": "string",
                                "format": "password",
                            },
                        },
                        "required": ["username", "password"],
                    }
                },
            }
        }
    },
)
async def login(
    creds: LoginCredentialsDep,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Authenticate with username/email and password, returning access and refresh tokens.

    Supports both:
    - Standard OAuth2 Form Data (`username` and `password`) used by Swagger UI Authorize dialog.
    - JSON payload with `identifier` (or `username`/`email`) and `password`.
    """
    user, tokens = await auth_service.login(creds)
    tokens.user = UserResponse.model_validate(user)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
)
async def refresh_token(
    req: RefreshTokenRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """Validate refresh token and return rotated access and refresh tokens."""
    return await auth_service.refresh(req.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="User logout",
)
async def logout(
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    req: LogoutRequest | None = None,
) -> MessageResponse:
    """Revoke refresh token and blacklist access token in Redis."""
    refresh_token = req.refresh_token if req else None
    await auth_service.logout(
        user_id=str(current_user["id"]),
        refresh_token_str=refresh_token,
        access_token_str=token,
    )
    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
)
async def get_user_profile(
    current_user: CurrentUserDep,
) -> UserResponse:
    """Fetch current authenticated user profile."""
    return UserResponse.model_validate(current_user)
