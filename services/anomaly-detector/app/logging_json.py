"""Logs structurés JSON (`service`, `trace_id`, `event`), exploitables dans Loki."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "at": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "service": "anomaly-detector",
            "trace_id": getattr(record, "trace_id", None),
            "event": getattr(record, "event", record.name),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        for key in ("score", "target_service", "kind"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
