from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique username containing letters, numbers, underscores, and hyphens",
    )
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="Plain text password"
    )


class UserLoginRequest(BaseModel):
    identifier: str = Field(
        ...,
        description="Username or email address",
        validation_alias=AliasChoices("identifier", "username", "email"),
    )
    password: str = Field(..., min_length=1, description="Password")


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user: UserResponse | None = Field(
        default=None, description="Authenticated user profile"
    )


AuthResponse = TokenResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = Field(
        default=None,
        description="Valid JWT refresh token (optional if provided in cookie)",
    )


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(
        default=None,
        description="Optional refresh token to revoke specifically",
    )


class MessageResponse(BaseModel):
    message: str
