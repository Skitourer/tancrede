"""Logging per profile (SPEC §11 rule 4, T-DEV-03).

In `real`, a log line carries only an event code, safe fields (IDs, error
codes, durations, counts) and the exception *type*. Message arguments,
free text and exception messages or tracebacks are dropped.

Convention for callers::

    log.info("router.call", extra={"gateway": "local", "duration_ms": 120})
"""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler

from tancrede.config.profiles import Profile, ProfilePaths

EVENT_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
SAFE_FIELDS = ("id", "code", "gateway", "task_kind", "count", "duration_ms")
REDACTED = "redacted"


def _safe_value(value: object) -> bool:
    if isinstance(value, bool | int | float):
        return True
    return isinstance(value, str) and EVENT_RE.match(value) is not None


class RealSafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.msg
        event = (
            msg if isinstance(msg, str) and not record.args and EVENT_RE.match(msg) else REDACTED
        )
        parts = [
            self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            record.levelname,
            record.name,
            f"event={event}",
        ]
        for field in SAFE_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                parts.append(f"{field}={value if _safe_value(value) else REDACTED}")
        if record.exc_info and record.exc_info[0] is not None:
            parts.append(f"exc={record.exc_info[0].__name__}")
        return " ".join(parts)


def configure_logging(profile: Profile, paths: ProfilePaths) -> None:
    root = logging.getLogger("tancrede")
    root.handlers.clear()
    root.propagate = False
    root.setLevel(logging.INFO)

    if profile is Profile.REAL:
        paths.logs_dir.mkdir(parents=True, exist_ok=True)
        formatter: logging.Formatter = RealSafeFormatter()
        file_handler = RotatingFileHandler(
            paths.logs_dir / "tancrede.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    stream.setLevel(logging.WARNING)
    root.addHandler(stream)
