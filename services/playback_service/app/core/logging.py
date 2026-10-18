import contextvars
import json
import logging
import os
import sys
import time
import traceback
import uuid
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any, ClassVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)

# Context variables for distributed tracing & request correlation
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
user_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def get_correlation_id() -> str | None:
    return correlation_id_ctx.get()


def get_user_id() -> str | None:
    return user_id_ctx.get()


def set_user_id(user_id: str | None) -> None:
    user_id_ctx.set(user_id)


class ContextualFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        record.correlation_id = correlation_id_ctx.get() or "-"
        record.user_id = user_id_ctx.get() or "-"
        record.service = getattr(
            record, "service", settings.service_name.replace("-", "_")
        )
        record.environment = settings.app_env
        return True


class StructuredJSONFormatter(logging.Formatter):
    STANDARD_ATTRS: ClassVar[set[str]] = {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
        "request_id",
        "correlation_id",
        "user_id",
        "service",
        "environment",
    }

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()

        log_entry: dict[str, Any] = {
            "timestamp": timestamp,
            "time": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "name": record.name,
            "message": record.getMessage(),
            "service": getattr(
                record, "service", settings.service_name.replace("-", "_")
            ),
            "environment": getattr(record, "environment", settings.app_env),
            "request_id": getattr(record, "request_id", "-"),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }

        user_id = getattr(record, "user_id", "-")
        if user_id and user_id != "-":
            log_entry["user_id"] = user_id

        extra_fields = {
            k: v for k, v in record.__dict__.items() if k not in self.STANDARD_ATTRS
        }
        if extra_fields:
            log_entry.update(extra_fields)

        if record.exc_info:
            exc_type, exc_val, _ = record.exc_info
            log_entry["exception"] = {
                "type": exc_type.__name__ if exc_type else "Exception",
                "message": str(exc_val) if exc_val else "",
                "stack_trace": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, default=str, ensure_ascii=False)


def setup_logging() -> None:
    """Configure structured logging for playback service."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.addFilter(ContextualFilter())
    stream_handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(stream_handler)

    # File handler for log aggregation (Promtail / Loki)
    log_dir = os.environ.get(
        "LOG_DIR",
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "..",
                "infra",
                "logs",
            )
        ),
    )
    if os.path.exists(log_dir):
        file_path = os.path.join(
            log_dir, f"{settings.service_name.replace('-', '_')}.log"
        )
        file_handler = RotatingFileHandler(
            file_path, maxBytes=20 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.addFilter(ContextualFilter())
        file_handler.setFormatter(StructuredJSONFormatter())
        root_logger.addHandler(file_handler)

    for uvicorn_logger_name in ("uvicorn", "uvicorn.error"):
        u_logger = logging.getLogger(uvicorn_logger_name)
        u_logger.handlers = root_logger.handlers
        u_logger.propagate = False

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.propagate = False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id") or request_id

        t_req = request_id_ctx.set(request_id)
        t_corr = correlation_id_ctx.set(correlation_id)

        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "-"
        user_agent = request.headers.get("user-agent", "-")

        is_health = request.url.path.endswith("/live") or request.url.path.endswith(
            "/ready"
        )

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id

            log_meta = {
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
                "user_agent": user_agent,
            }

            if is_health:
                logger.debug("Health probe checked", extra=log_meta)
            elif response.status_code >= 500:
                logger.error("HTTP request error", extra=log_meta)
            elif response.status_code >= 400:
                logger.warning("HTTP request client error", extra=log_meta)
            else:
                logger.info("HTTP request completed", extra=log_meta)

            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "Unhandled exception occurred while processing request",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                },
            )
            raise
        finally:
            request_id_ctx.reset(t_req)
            correlation_id_ctx.reset(t_corr)
            user_id_ctx.set(None)
