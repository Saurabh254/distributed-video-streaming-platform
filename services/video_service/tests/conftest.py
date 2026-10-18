from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def create_test_token(
    user_id: str | None = None,
    username: str = "testuser",
    email: str = "test@example.com",
    expired: bool = False,
    token_type: str = "access",
) -> str:
    uid = user_id or str(uuid4())
    now = datetime.now(UTC)
    exp = now - timedelta(minutes=5) if expired else now + timedelta(minutes=30)
    payload = {
        "sub": uid,
        "username": username,
        "email": email,
        "type": token_type,
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


@pytest.fixture
def client():
    """Synchronous TestClient managing FastAPI lifespan."""
    with TestClient(app) as test_client:
        yield test_client
