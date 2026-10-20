"""Publication des événements en JSON, une ligne par événement (stdout -> Alloy -> Loki)."""

from __future__ import annotations

import json
from typing import TextIO

from app.domain.models import RagEvent


class JsonStdoutPublisher:
    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def publish(self, event: RagEvent) -> None:
        record = {
            "service": event.service,
            "trace_id": event.trace_id,
            "event": event.event,
            "at": event.at.isoformat(),
            "data": event.data,
        }
        self._stream.write(json.dumps(record, default=str) + "\n")
        self._stream.flush()
