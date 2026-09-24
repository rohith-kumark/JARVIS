import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records as structured JSON for production observability.
    In development, fallback or plain formatted output can be used.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Include custom extra fields if provided
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message"
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in standard_attrs}
        if extras:
            log_payload["extra"] = extras

        return json.dumps(log_payload)


class PrettyConsoleFormatter(logging.Formatter):
    """
    Colorized/clear console formatter for local interactive development.
    """
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[41m", # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"{color}[{timestamp}] [{record.levelname:<7}] [{record.name}]:{self.RESET} {record.getMessage()}"
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        return formatted


def setup_logging(level: str = "INFO", structured: bool = False) -> logging.Logger:
    """Configure root logger with either structured JSON or pretty console format."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers to prevent duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if structured:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(PrettyConsoleFormatter())

    root_logger.addHandler(handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return root_logger
