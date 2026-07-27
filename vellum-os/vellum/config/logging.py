"""
Vellum OS — Structured Logging (structlog 26.x)

Configures structlog with JSON output for production and
human-readable console output for development.
"""

from __future__ import annotations

import logging
import sys

import structlog


class EndpointFilter(logging.Filter):
    """Filter out routine HTTP GET polling and static asset access logs from Uvicorn."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # Filter out noisy routine GETs & static assets
        noisy_patterns = (
            "GET /api/status",
            "GET /api/jobs",
            "GET /api/outreach",
            "GET /api/profile",
            "GET /styles.css",
            "GET /app.js",
            "GET /assets/",
            "WebSocket /ws",
            "connection open",
        )
        return not any(pattern in msg for pattern in noisy_patterns)


def setup_logging(log_level: str = "INFO", json_output: bool = False) -> None:
    """Configure structlog and stdlib logging.

    Args:
        log_level: Standard log level string (DEBUG, INFO, WARNING, ERROR).
        json_output: If True, emit JSON lines. If False, use console renderer.
    """
    # Silence LiteLLM debug output
    try:
        import litellm
        litellm.suppress_debug_info = True
        litellm.set_verbose = False
    except ImportError:
        pass

    for logger_name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy", "httpx", "httpcore"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib root logger so third-party libs are captured
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Apply Uvicorn access filter to clean up terminal polling noise
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.addFilter(EndpointFilter())


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a bound structlog logger, optionally scoped by name."""
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(component=name)
    return logger

