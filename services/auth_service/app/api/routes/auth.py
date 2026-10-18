from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.core.config import settings
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


def _set_auth_cookies(response: Response, tokens: TokenResponse) -> None:
    is_prod = settings.app_env == "production"
    # HttpOnly, SameSite=Lax cookie for refresh token rotation
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    req: UserRegisterRequest,
    auth_service: AuthServiceDep,
    response: Response,
) -> TokenResponse:
    """Register a new user, return tokens, and set HttpOnly refresh token cookie."""
    user, tokens = await auth_service.register(req)
    tokens.user = UserResponse.model_validate(user)
    _set_auth_cookies(response, tokens)
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
    response: Response,
) -> TokenResponse:
    """Authenticate credentials, return tokens, and set HttpOnly refresh token cookie."""
    user, tokens = await auth_service.login(creds)
    tokens.user = UserResponse.model_validate(user)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
)
async def refresh_token(
    auth_service: AuthServiceDep,
    response: Response,
    req: RefreshTokenRequest | None = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
) -> TokenResponse:
    """Validate refresh token from JSON body or HttpOnly cookie and return rotated tokens."""
    token_str = (
        req.refresh_token if req and req.refresh_token else None
    ) or refresh_token_cookie
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required in body or cookie",
        )
    tokens = await auth_service.refresh(token_str)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="User logout",
)
async def logout(
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
    response: Response,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    req: LogoutRequest | None = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
) -> MessageResponse:
    """Revoke refresh token, blacklist access token in Redis, and clear HttpOnly cookie."""
    ref_token = (
        req.refresh_token if req and req.refresh_token else None
    ) or refresh_token_cookie
    await auth_service.logout(
        user_id=str(current_user["id"]),
        refresh_token_str=ref_token,
        access_token_str=token,
    )
    _clear_auth_cookies(response)
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
