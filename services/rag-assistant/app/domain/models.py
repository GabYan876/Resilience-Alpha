"""Modèles du domaine de l'assistant RAG : aucune dépendance framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

SERVICE = "rag-assistant"


@dataclass(frozen=True)
class Document:
    """Un fichier du corpus ; `source` est son chemin relatif (affiché comme citation)."""

    source: str
    text: str


@dataclass(frozen=True)
class Passage:
    """Un extrait de document retrouvé pour répondre à une question."""

    source: str
    text: str


@dataclass(frozen=True)
class Answer:
    text: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class RagEvent:
    """Événement structuré (JSON) consommé par Loki : jamais le texte de la question."""

    event: str
    trace_id: str
    data: dict[str, Any] = field(default_factory=dict)
    service: str = SERVICE
    at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InvalidQuestion(ValueError):
    """Question vide ou trop longue."""


class AssistantUnavailable(Exception):
    """Ollama injoignable ou en erreur : le service reste vivant, la réponse est impossible."""
