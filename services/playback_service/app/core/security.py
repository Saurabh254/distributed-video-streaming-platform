import logging
from typing import Any

import jwt
from fastapi import Request

from app.core.config import settings

logger = logging.getLogger(__name__)


def extract_user_id_from_request(request: Request) -> str | None:
    """Extract user_id from Authorization header if present."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return str(payload.get("sub"))
    except jwt.PyJWTError as e:
        logger.debug("Failed to decode JWT token: %s", e)
        return None
