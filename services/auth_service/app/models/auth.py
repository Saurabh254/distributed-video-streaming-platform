from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class User:
    id: UUID
    username: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class UserPassword:
    user_id: UUID
    password_hash: str
    salt: str
    algorithm: str
    iterations: int
    created_at: datetime
    updated_at: datetime
