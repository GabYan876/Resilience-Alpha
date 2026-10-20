import pytest

from app.config import Settings


def test_token_is_required(monkeypatch):
    monkeypatch.delenv("RAG_TOKEN", raising=False)
    with pytest.raises(KeyError):
        Settings.from_env()


def test_empty_token_is_refused(monkeypatch):
    monkeypatch.setenv("RAG_TOKEN", "")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_defaults_and_overrides(monkeypatch):
    monkeypatch.setenv("RAG_TOKEN", "jeton-de-test")
    settings = Settings.from_env()
    assert settings.llm_model == "llama3.1:8b"
    assert settings.top_k == 8

    monkeypatch.setenv("LLM_MODEL", "mistral:7b")
    monkeypatch.setenv("TOP_K", "6")
    settings = Settings.from_env()
    assert (settings.llm_model, settings.top_k) == ("mistral:7b", 6)
