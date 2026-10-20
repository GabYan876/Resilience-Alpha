"""Cas d'usage : construire l'index à partir du corpus (lecture seule)."""

from __future__ import annotations

import threading

from app.domain.models import AssistantUnavailable, RagEvent
from app.domain.ports import DocumentSource, EventPublisher, PassageIndexer


class IndexingService:
    def __init__(
        self, source: DocumentSource, indexer: PassageIndexer, publisher: EventPublisher
    ) -> None:
        self._source = source
        self._indexer = indexer
        self._publisher = publisher
        self._lock = threading.Lock()
        self._chunks = 0

    @property
    def chunk_count(self) -> int:
        return self._chunks

    def reindex(self, trace_id: str) -> int:
        with self._lock:
            return self._run(trace_id)

    def ensure_indexed(self, trace_id: str) -> None:
        """Indexe au premier besoin (Ollama peut démarrer après l'assistant)."""
        if self._chunks:
            return
        with self._lock:
            if not self._chunks:
                self._run(trace_id)

    def _run(self, trace_id: str) -> int:
        documents = self._source.read_all()
        try:
            chunks = self._indexer.index(documents)
        except AssistantUnavailable:
            self._publisher.publish(RagEvent("rag.index_failed", trace_id))
            raise
        self._chunks = chunks
        self._publisher.publish(
            RagEvent("rag.indexed", trace_id, {"documents": len(documents), "chunks": chunks})
        )
        return chunks
