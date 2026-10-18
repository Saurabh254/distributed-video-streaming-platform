import contextvars
import json
import logging
import sys
import time
import traceback
import uuid
from datetime import UTC, datetime
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
        record.service = settings.service_name
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
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": getattr(record, "service", settings.service_name),
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


class ColoredConsoleFormatter(logging.Formatter):
    LEVEL_STYLES: ClassVar[dict[int, str]] = {
        logging.DEBUG: "\033[36mDEBUG  \033[0m",
        logging.INFO: "\033[32mINFO   \033[0m",
        logging.WARNING: "\033[33mWARN   \033[0m",
        logging.ERROR: "\033[31mERROR  \033[0m",
        logging.CRITICAL: "\033[1;35mFATAL  \033[0m",
    }

    METHOD_COLORS: ClassVar[dict[str, str]] = {
        "GET": "\033[36m",
        "POST": "\033[32m",
        "PUT": "\033[33m",
        "PATCH": "\033[33m",
        "DELETE": "\033[31m",
        "OPTIONS": "\033[35m",
        "HEAD": "\033[34m",
    }

    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"

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
        "http_method",
        "http_path",
        "http_status",
        "duration_ms",
        "client_ip",
        "user_agent",
    }

    def format(self, record: logging.LogRecord) -> str:
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_badge = self.LEVEL_STYLES.get(record.levelno, f"{record.levelname:<7s}")

        req_id = getattr(record, "request_id", None)
        req_suffix = (
            f" {self.DIM}req={req_id[:8]}{self.RESET}"
            if req_id and req_id != "-"
            else ""
        )

        user_id = getattr(record, "user_id", None)
        user_suffix = (
            f" {self.DIM}user={user_id[:8]}{self.RESET}"
            if user_id and user_id != "-"
            else ""
        )

        if hasattr(record, "http_method") and hasattr(record, "http_status"):
            method = getattr(record, "http_method", "")
            method_color = self.METHOD_COLORS.get(method, self.RESET)
            method_str = f"{method_color}{self.BOLD}{method:<6s}{self.RESET}"
            path_str = f"{self.BOLD}{getattr(record, 'http_path', '')}{self.RESET}"

            status_code = getattr(record, "http_status", 0)
            if status_code < 300:
                status_color = "\033[32m"
            elif status_code < 400:
                status_color = "\033[36m"
            elif status_code < 500:
                status_color = "\033[33m"
            else:
                status_color = "\033[31m"

            status_str = f"{status_color}{status_code}{self.RESET}"
            dur = getattr(record, "duration_ms", 0.0)
            dur_color = (
                "\033[32m" if dur < 50 else ("\033[33m" if dur < 200 else "\033[31m")
            )
            dur_str = f"{dur_color}({dur:.1f}ms){self.RESET}"

            client_ip = getattr(record, "client_ip", "-")
            ip_str = (
                f" {self.DIM}ip={client_ip}{self.RESET}" if client_ip != "-" else ""
            )

            msg = (
                f"{self.DIM}[{time_str}]{self.RESET} {level_badge} "
                f"{method_str} {path_str} {status_str} {dur_str}{req_suffix}{user_suffix}{ip_str}"
            )
        else:
            short_logger = record.name.rsplit(".", 1)[-1]
            logger_tag = f"{self.DIM}[{short_logger}]{self.RESET}"

            extras = [
                f"{self.DIM}{k}={v}{self.RESET}"
                for k, v in record.__dict__.items()
                if k not in self.STANDARD_ATTRS
            ]
            extras_str = f" {' '.join(extras)}" if extras else ""

            msg = (
                f"{self.DIM}[{time_str}]{self.RESET} {level_badge} "
                f"{logger_tag} {record.getMessage()}{extras_str}{req_suffix}{user_suffix}"
            )

        if record.exc_info:
            msg += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return msg


def setup_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.addFilter(ContextualFilter())

    if settings.log_format == "json":
        stream_handler.setFormatter(StructuredJSONFormatter())
    else:
        stream_handler.setFormatter(ColoredConsoleFormatter())

    root_logger.addHandler(stream_handler)

    for uvicorn_logger_name in ("uvicorn", "uvicorn.error"):
        u_logger = logging.getLogger(uvicorn_logger_name)
        u_logger.handlers = [stream_handler]
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
