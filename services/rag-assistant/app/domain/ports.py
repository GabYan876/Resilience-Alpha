"""Ports de l'assistant RAG.

Petits et ciblés (ISP) : lire le corpus, l'indexer, retrouver des passages, générer une
réponse et publier un événement sont cinq responsabilités distinctes. Aucun port ne permet
d'écrire dans le corpus ni d'agir sur l'infrastructure : l'assistant est en lecture seule.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.domain.models import Document, Passage, RagEvent


class DocumentSource(Protocol):
    def read_all(self) -> Sequence[Document]: ...


class PassageIndexer(Protocol):
    def index(self, documents: Sequence[Document]) -> int:
        """Remplace l'index par ces documents ; retourne le nombre d'extraits indexés."""
        ...


class PassageRetriever(Protocol):
    def search(self, query: str, k: int) -> Sequence[Passage]: ...


class AnswerGenerator(Protocol):
    def generate(self, question: str, passages: Sequence[Passage]) -> str: ...


class EventPublisher(Protocol):
    def publish(self, event: RagEvent) -> None: ...
