"""Structured key=value logging for quote-box.

Emits one line per record like::

    ts=2026-05-22T22:57:01 level=INFO logger=app.main msg="server starting" port=8035

Readable in ``journalctl -u quote-box`` and parseable by anything that splits on
whitespace honoring quoted strings. Any ``extra={...}`` fields passed to a log
call are appended as additional ``key=value`` pairs.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

_RESERVED_LOGRECORD_ATTRS: frozenset[str] = frozenset(
    {
        "args",
        "asctime",
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
    }
)


def _format_value(value: Any) -> str:
    text = str(value)
    if any(c.isspace() for c in text) or '"' in text:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


class KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="seconds")
        parts: list[str] = [
            f"ts={ts}",
            f"level={record.levelname}",
            f"logger={record.name}",
            f"msg={_format_value(record.getMessage())}",
        ]
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOGRECORD_ATTRS or key.startswith("_"):
                continue
            parts.append(f"{key}={_format_value(value)}")
        if record.exc_info:
            parts.append(f"exc={_format_value(self.formatException(record.exc_info))}")
        return " ".join(parts)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if any(getattr(h, "_quote_box", False) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(KeyValueFormatter())
    setattr(handler, "_quote_box", True)
    root.addHandler(handler)
    root.setLevel(level)
