"""Index vectoriel en mémoire (LangChain) : découpe, embeddings Ollama, recherche par similarité.

Pas de base vectorielle externe : le corpus tient en quelques centaines d'extraits, et un
conteneur de moins économise de la RAM. L'index est reconstruit à chaque `index()`, puis
substitué d'un bloc : une recherche en cours voit l'ancien ou le nouvel index, jamais un mélange.
"""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import MarkdownTextSplitter

from app.domain.models import AssistantUnavailable, Document, Passage


class LangChainPassageIndex:
    def __init__(
        self, embeddings: Embeddings, chunk_size: int = 800, chunk_overlap: int = 100
    ) -> None:
        self._embeddings = embeddings
        self._splitter = MarkdownTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self._store: InMemoryVectorStore | None = None

    def index(self, documents: Sequence[Document]) -> int:
        chunks = self._splitter.create_documents(
            [d.text for d in documents], metadatas=[{"source": d.source} for d in documents]
        )
        store = InMemoryVectorStore(self._embeddings)
        try:
            if chunks:
                store.add_documents(chunks)
        except Exception as exc:  # frontière : toute erreur Ollama devient « indisponible »
            raise AssistantUnavailable("embeddings indisponibles") from exc
        self._store = store
        return len(chunks)

    def search(self, query: str, k: int) -> list[Passage]:
        store = self._store
        if store is None:
            return []
        try:
            found = store.similarity_search(query, k=k)
        except Exception as exc:
            raise AssistantUnavailable("embeddings indisponibles") from exc
        return [Passage(str(d.metadata["source"]), d.page_content) for d in found]
