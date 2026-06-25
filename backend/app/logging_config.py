"""Structured (JSON) logging for production deployments.

Uses only the standard library — no extra dependency — so it never breaks the
zero-config invariant. ``configure_logging()`` is idempotent and is called once
on application startup. A request-id is attached to log records via a contextvar
so every line emitted during a request can be correlated.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Set per-request by the request-id middleware; read by the formatter.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_RESERVED = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        rid = request_id_var.get()
        if rid:
            payload["request_id"] = rid

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        # Promote any structured extras passed via logger.info(..., extra={...}).
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_") and key not in payload:
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Install the JSON handler on the root logger (idempotent).

    Honors ``LOG_LEVEL`` (default INFO) and ``LOG_FORMAT`` (``json`` default, or
    ``plain`` for human-readable local dev).
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Replace any handlers we previously installed so repeated calls are safe.
    for handler in list(root.handlers):
        if getattr(handler, "_ads_handler", False):
            root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler._ads_handler = True  # type: ignore[attr-defined]
    if os.getenv("LOG_FORMAT", "json").lower() == "plain":
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    else:
        handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # uvicorn installs its own handlers; let our root handler format their records.
    for noisy in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        lg = logging.getLogger(noisy)
        lg.handlers.clear()
        lg.propagate = True
