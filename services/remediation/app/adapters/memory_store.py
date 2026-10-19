"""Mémoire bornée des incidents (en mémoire du processus : la preuve durable est dans Loki)."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from threading import Lock

from app.domain.models import Incident


class InMemoryIncidentStore:
    def __init__(self, capacity: int = 200) -> None:
        self._capacity = capacity
        self._incidents: OrderedDict[str, Incident] = OrderedDict()
        self._lock = Lock()  # les routes synchrones de FastAPI tournent dans un pool de threads

    def save(self, incident: Incident) -> None:
        with self._lock:
            self._incidents[incident.id] = incident
            self._incidents.move_to_end(incident.id)
            while len(self._incidents) > self._capacity:
                self._incidents.popitem(last=False)

    def get(self, incident_id: str) -> Incident | None:
        with self._lock:
            return self._incidents.get(incident_id)

    def list_recent(self, limit: int) -> Sequence[Incident]:
        with self._lock:
            return list(reversed(self._incidents.values()))[:limit]
