"""
Kuro OS — Premium Terminal Logging Configuration

Clean, high-visibility, colorized structured logging for Kuro OS agents.
Silences third-party library spam (ddgs, curl_cffi, httpx, litellm, etc.) and
presents clean step-by-step agent telemetry in the terminal.
"""

from __future__ import annotations

import logging
import sys
try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


class EndpointFilter(logging.Filter):
    """Filter out routine HTTP GET polling and static asset access logs from Uvicorn."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
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
            "POST /api/status",
            "response: https://",
        )
        return not any(pattern in msg for pattern in noisy_patterns)


if HAS_STRUCTLOG:
    class PremiumConsoleRenderer:
        """Custom high-fidelity console renderer for structlog."""
        def __init__(self, colors: bool = True):
            self.colors = colors

        def __call__(self, logger: logging.Logger, name: str, event_dict: dict) -> str:
            timestamp = event_dict.pop("timestamp", "")
            level = event_dict.pop("level", "info").lower()
            component = event_dict.pop("component", None)
            event = event_dict.pop("event", "")
            exception = event_dict.pop("exception", None)

            # Color codes
            RESET = "\033[0m"
            GRAY = "\033[90m"
            BOLD = "\033[1m"
            
            # Level styles (clean, modern icons)
            level_styles = {
                "debug": ("\033[36m", "⚙"),
                "info": ("\033[32m", "✔"),
                "warning": ("\033[33m", "⚠"),
                "error": ("\033[31m", "✖"),
                "critical": ("\033[35m\033[1m", "💥"),
            }
            
            color, icon = level_styles.get(level, ("\033[32m", "✔"))
            
            if not self.colors:
                color, icon, RESET, GRAY, BOLD = "", "", "", "", ""

            # Formatted timestamp
            time_str = f"{GRAY}{timestamp}{RESET} " if timestamp else ""
            
            # Formatted level
            level_str = f"{color}{icon} {level.upper():<5}{RESET} "
            
            # Formatted component
            comp_str = f"{BOLD}\033[34m[{component.upper()}]\033[0m " if component else ""
            
            # Formatted event
            if level in ("error", "critical"):
                event_str = f"{BOLD}{event}{RESET}"
            elif level == "warning":
                event_str = f"\033[33m{event}\033[0m"
            else:
                event_str = f"{event}"
            
            # Formatted key-value pairs (neatly aligned using bullets)
            kv_pairs = []
            for k, v in event_dict.items():
                if k.startswith("_"):
                     continue
                if isinstance(v, float):
                    v_str = f"{v:.1f}"
                else:
                    v_str = str(v)
                kv_pairs.append(f"{GRAY}{k}={RESET}{v_str}")
            
            separator = f" {GRAY}|{RESET} "
            kv_str = f"  {separator}" + separator.join(kv_pairs) if kv_pairs else ""
            
            res = f"{time_str}{level_str}{comp_str}{event_str}{kv_str}"
            if exception:
                res += f"\n{GRAY}{exception}{RESET}"
            return res


def setup_logging(log_level: str = "INFO", json_output: bool = False) -> None:
    """Configure structlog and stdlib logging with clean console output."""
    try:
        import litellm
        litellm.suppress_debug_info = True
        litellm.set_verbose = False
    except ImportError:
        pass

    # Suppress LiteLLM Gemini deprecation warnings about temperature/top_p/top_k
    # These are cosmetic — the params still work but LiteLLM logs noisy warnings
    import warnings as _warnings
    _warnings.filterwarnings(
        "ignore",
        message=".*temperature.*top_p.*top_k.*continue to function.*",
        category=DeprecationWarning,
        module="litellm",
    )
    _warnings.filterwarnings(
        "ignore",
        message=".*DeprecationWarning.*temperature.*",
        category=DeprecationWarning,
    )
    # Broadly suppress DeprecationWarnings from litellm vertex module
    _warnings.filterwarnings("ignore", category=DeprecationWarning, module="litellm.*")

    noisy_loggers = (
        "LiteLLM", "LiteLLM Router", "LiteLLM Proxy",
        "httpx", "httpcore", "curl_cffi", "ddgs",
        "duckduckgo_search", "urllib3", "watchfiles",
        "asyncio", "scrapegraphai"
    )
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    if HAS_STRUCTLOG:
        shared_processors: list[structlog.types.Processor] = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]

        if json_output:
            renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
        else:
            renderer = PremiumConsoleRenderer(colors=sys.stderr.isatty())

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

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.addFilter(EndpointFilter())


class StandardLoggerAdapter:
    """Simple wrapper exposing structlog-compatible .info(), .warning(), .error()."""
    def __init__(self, name: str = "vellum"):
        self.logger = logging.getLogger(name)

    def info(self, event: str, **kwargs):
        self.logger.info(f"{event} {kwargs if kwargs else ''}")

    def warning(self, event: str, **kwargs):
        self.logger.warning(f"{event} {kwargs if kwargs else ''}")

    def error(self, event: str, **kwargs):
        self.logger.error(f"{event} {kwargs if kwargs else ''}")

    def debug(self, event: str, **kwargs):
        self.logger.debug(f"{event} {kwargs if kwargs else ''}")


def get_logger(name: str | None = None):
    """Get a bound structlog logger or standard fallback logger."""
    if HAS_STRUCTLOG:
        logger = structlog.get_logger()
        if name:
            logger = logger.bind(component=name)
        return logger
    else:
        return StandardLoggerAdapter(name or "vellum")
