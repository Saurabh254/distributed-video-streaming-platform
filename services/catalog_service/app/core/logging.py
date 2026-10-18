import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging for catalog service."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.log_format == "console":
        handler = RichHandler(
            console=Console(file=sys.stderr),
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
        )
        formatter = logging.Formatter("%(message)s")
    else:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            '{"time":"%(asctime)s","name":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'
        )

    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]
