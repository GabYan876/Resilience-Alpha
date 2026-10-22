"""Fakes en mémoire des ports (substituables aux adaptateurs de prod, LSP)."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.models import AssistantUnavailable, Document, Passage, RagEvent


class FakeSource:
    def __init__(self, documents: Sequence[Document] = ()) -> None:
        self._documents = list(documents)

    def read_all(self) -> list[Document]:
        return list(self._documents)


class FakeIndex:
    """Joue à la fois l'indexeur et le retriever (comme l'adaptateur LangChain)."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.index_calls = 0
        self.passages: list[Passage] = []

    def index(self, documents: Sequence[Document]) -> int:
        self.index_calls += 1
        if self.fail:
            raise AssistantUnavailable("embeddings indisponibles")
        self.passages = [Passage(d.source, d.text) for d in documents]
        return len(self.passages)

    def search(self, query: str, k: int) -> list[Passage]:
        return self.passages[:k]


class FakeGenerator:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, list[Passage]]] = []

    def generate(self, question: str, passages: Sequence[Passage]) -> str:
        if self.fail:
            raise AssistantUnavailable("modèle de langage indisponible")
        self.calls.append((question, list(passages)))
        return f"réponse à : {question}"


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[RagEvent] = []

    def publish(self, event: RagEvent) -> None:
        self.events.append(event)

    @property
    def names(self) -> list[str]:
        return [e.event for e in self.events]
