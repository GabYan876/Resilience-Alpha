import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.embeddings.fake import DeterministicFakeEmbedding

from app.adapters.langchain_index import LangChainPassageIndex
from app.domain.models import AssistantUnavailable, Document

DOCS = [
    Document("docs/attaque.md", "# Attaque\n\nLe flood HTTP sature le pool de connexions."),
    Document("docs/rag.md", "# RAG\n\nL'assistant est en lecture seule sur le réseau rag."),
]


class BrokenEmbeddings(Embeddings):
    def embed_documents(self, texts):
        raise ConnectionError("ollama injoignable")

    def embed_query(self, text):
        raise ConnectionError("ollama injoignable")


def test_search_before_indexing_is_empty():
    assert LangChainPassageIndex(DeterministicFakeEmbedding(size=16)).search("x", 3) == []


def test_index_then_search_returns_the_closest_chunk_with_its_source():
    index = LangChainPassageIndex(DeterministicFakeEmbedding(size=32))
    assert index.index(DOCS) == 2

    # Embeddings factices déterministes : le texte exact d'un extrait en est le plus proche.
    found = index.search(DOCS[1].text, k=1)

    assert [p.source for p in found] == ["docs/rag.md"]
    assert "lecture seule" in found[0].text


def test_long_document_is_split_and_k_is_respected():
    index = LangChainPassageIndex(
        DeterministicFakeEmbedding(size=16), chunk_size=100, chunk_overlap=0
    )
    long_doc = Document(
        "docs/long.md", "\n\n".join(f"Paragraphe {i} " + "mot " * 20 for i in range(6))
    )
    assert index.index([long_doc]) > 2
    assert len(index.search("Paragraphe", k=2)) == 2


def test_reindex_replaces_previous_content():
    index = LangChainPassageIndex(DeterministicFakeEmbedding(size=16))
    index.index(DOCS)
    index.index([Document("docs/neuf.md", "neuf")])
    assert {p.source for p in index.search("neuf", k=5)} == {"docs/neuf.md"}


def test_failed_reindex_raises_and_keeps_the_previous_index():
    index = LangChainPassageIndex(DeterministicFakeEmbedding(size=16))
    index.index(DOCS)
    index._embeddings = BrokenEmbeddings()  # Ollama tombe après la première construction

    with pytest.raises(AssistantUnavailable):
        index.index(DOCS)

    assert len(index.search("Attaque", k=2)) == 2  # l'ancien index reste interrogeable


def test_query_embedding_failure_becomes_assistant_unavailable():
    class QueryFails(DeterministicFakeEmbedding):
        def embed_query(self, text):
            raise ConnectionError("ollama injoignable")

    index = LangChainPassageIndex(QueryFails(size=16))
    index.index(DOCS)

    with pytest.raises(AssistantUnavailable):
        index.search("x", 1)
