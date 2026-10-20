from fastapi.testclient import TestClient
from langchain_core.embeddings.fake import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config import Settings
from app.main import create_app

TOKEN = "test-token"  # placeholder de test, pas un vrai secret
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class FailingChatModel(FakeListChatModel):
    def _call(self, *args, **kwargs):
        raise TimeoutError("ollama ne répond pas")


def make_client(tmp_path, chat_model=None, max_question_chars=100) -> TestClient:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "equipe.md").write_text(
        "# Équipe\n\nKevin est tech lead.", encoding="utf-8"
    )
    settings = Settings(
        rag_token=TOKEN, corpus_path=str(tmp_path), max_question_chars=max_question_chars
    )
    app = create_app(
        settings,
        embeddings=DeterministicFakeEmbedding(size=16),
        chat_model=chat_model or FakeListChatModel(responses=["Kevin."]),
    )
    return TestClient(app)


def test_health_is_open(tmp_path):
    assert make_client(tmp_path).get("/health").json() == {"status": "ok", "indexed_chunks": 0}


def test_ask_and_reindex_require_token(tmp_path):
    client = make_client(tmp_path)
    assert client.post("/ask", json={"question": "Qui ?"}).status_code == 401
    bad = client.post("/ask", json={"question": "Qui ?"}, headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401
    assert client.post("/reindex").status_code == 401


def test_ask_answers_with_sources_and_indexes_on_demand(tmp_path):
    client = make_client(tmp_path)

    response = client.post("/ask", json={"question": "Qui est tech lead ?"}, headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Kevin."
    assert body["sources"] == ["docs/equipe.md"]
    assert body["trace_id"]
    assert client.get("/health").json()["indexed_chunks"] == 1


def test_reindex_returns_chunk_count(tmp_path):
    client = make_client(tmp_path)
    assert client.post("/reindex", headers=AUTH).json() == {"chunks": 1}


def test_empty_or_too_long_question_is_422(tmp_path):
    client = make_client(tmp_path, max_question_chars=10)
    for question in ("   ", "x" * 11):
        response = client.post("/ask", json={"question": question}, headers=AUTH)
        assert response.status_code == 422


def test_unreachable_model_is_503_not_a_crash(tmp_path):
    client = make_client(tmp_path, chat_model=FailingChatModel(responses=["x"]))
    response = client.post("/ask", json={"question": "Qui ?"}, headers=AUTH)
    assert response.status_code == 503
    assert client.get("/health").status_code == 200
