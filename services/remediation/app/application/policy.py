"""Politique de décision : choisit les actions selon la nature de l'incident."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.domain.models import Incident, IncidentKind
from app.domain.ports import RemediationAction


class KindBasedPolicy:
    """Registre `IncidentKind -> actions ordonnées`.

    Nouveau type d'incident = nouvelle entrée dans le registre, sans modifier la classe (OCP).
    """

    def __init__(self, registry: Mapping[IncidentKind, Sequence[RemediationAction]]) -> None:
        self._registry = registry

    def decide(self, incident: Incident) -> Sequence[RemediationAction]:
        return self._registry.get(incident.kind, ())
