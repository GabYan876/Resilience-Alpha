"""Publication des événements en JSON, une ligne par événement (stdout -> Alloy -> Loki)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TextIO


class JsonEventPublisher:
    """Implémente le port `EventPublisher`.

    Ne journalise jamais un secret ni une valeur de jeton.
    """

    def __init__(self, stream: TextIO, service: str = "api") -> None:
        self._stream = stream
        self._service = service

    def publish(self, event: str, trace_id: str, **data: object) -> None:
        record = {
            "service": self._service,
            "trace_id": trace_id,
            "event": event,
            "at": datetime.now(UTC).isoformat(),
            "data": data,
        }
        self._stream.write(json.dumps(record, default=str) + "\n")
        self._stream.flush()
