import json
import logging
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.logging import (
    ColoredConsoleFormatter,
    ContextualFilter,
    RequestLoggingMiddleware,
    StructuredJSONFormatter,
    correlation_id_ctx,
    get_correlation_id,
    get_request_id,
    get_user_id,
    request_id_ctx,
    set_user_id,
    setup_logging,
)


def test_structured_json_formatter():
    formatter = StructuredJSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="User authenticated: %s",
        args=("alice",),
        exc_info=None,
    )
    record.request_id = "req-12345"
    record.correlation_id = "corr-67890"
    record.user_id = "user-999"
    record.client_ip = "127.0.0.1"

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "User authenticated: alice"
    assert parsed["request_id"] == "req-12345"
    assert parsed["correlation_id"] == "corr-67890"
    assert parsed["user_id"] == "user-999"
    assert parsed["client_ip"] == "127.0.0.1"
    assert parsed["service"] == settings.service_name
    assert "timestamp" in parsed


def test_structured_json_formatter_with_exception():
    formatter = StructuredJSONFormatter()
    try:
        raise ValueError("Invalid credentials error")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=20,
        msg="An error occurred",
        args=(),
        exc_info=exc_info,
    )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "ERROR"
    assert "exception" in parsed
    assert parsed["exception"]["type"] == "ValueError"
    assert parsed["exception"]["message"] == "Invalid credentials error"
    assert len(parsed["exception"]["stack_trace"]) > 0


def test_colored_console_formatter():
    formatter = ColoredConsoleFormatter()
    record = logging.LogRecord(
        name="console_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=30,
        msg="Rate limit threshold reached",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-99999999"

    output = formatter.format(record)
    assert "Rate limit threshold reached" in output
    assert "WARN" in output
    assert "req=req-9999" in output

    # Test HTTP request record formatting
    http_record = logging.LogRecord(
        name="app.core.logging",
        level=logging.INFO,
        pathname="test.py",
        lineno=40,
        msg="HTTP request completed",
        args=(),
        exc_info=None,
    )
    http_record.http_method = "POST"
    http_record.http_path = "/api/v1/auth/login"
    http_record.http_status = 200
    http_record.duration_ms = 12.5
    http_record.request_id = "req-12345678"

    http_output = formatter.format(http_record)
    assert "POST" in http_output
    assert "/api/v1/auth/login" in http_output
    assert "200" in http_output
    assert "12.5ms" in http_output


def test_contextual_filter():
    filter_ = ContextualFilter()
    record = logging.LogRecord(
        name="filter_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=40,
        msg="Test filter",
        args=(),
        exc_info=None,
    )

    t_req = request_id_ctx.set("custom-req-id")
    t_corr = correlation_id_ctx.set("custom-corr-id")
    set_user_id("custom-user-id")

    try:
        assert filter_.filter(record) is True
        assert record.request_id == "custom-req-id"
        assert record.correlation_id == "custom-corr-id"
        assert record.user_id == "custom-user-id"
        assert record.service == settings.service_name
    finally:
        request_id_ctx.reset(t_req)
        correlation_id_ctx.reset(t_corr)
        set_user_id(None)


def test_request_logging_middleware():
    test_app = FastAPI()
    test_app.add_middleware(RequestLoggingMiddleware)

    @test_app.get("/ping")
    def ping():
        return {
            "req_id": get_request_id(),
            "corr_id": get_correlation_id(),
            "user_id": get_user_id(),
        }

    client = TestClient(test_app)

    # 1. Without client request ID headers (auto-generated)
    res = client.get("/ping")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    generated_req_id = res.headers["X-Request-ID"]
    body = res.json()
    assert body["req_id"] == generated_req_id
    assert body["corr_id"] == generated_req_id

    # 2. With incoming X-Request-ID and X-Correlation-ID
    custom_headers = {
        "X-Request-ID": "incoming-request-111",
        "X-Correlation-ID": "incoming-corr-222",
    }
    res_custom = client.get("/ping", headers=custom_headers)
    assert res_custom.status_code == 200
    assert res_custom.headers["X-Request-ID"] == "incoming-request-111"
    body_custom = res_custom.json()
    assert body_custom["req_id"] == "incoming-request-111"
    assert body_custom["corr_id"] == "incoming-corr-222"


def test_setup_logging():
    setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) > 0
    assert any(isinstance(f, ContextualFilter) for f in root.handlers[0].filters)
