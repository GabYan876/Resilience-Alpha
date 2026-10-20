"""Lecture de la configuration et des secrets : seul endroit qui touche à l'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    rag_token: str  # protège POST /ask et POST /reindex
    ollama_url: str = "http://host.docker.internal:11434"  # Ollama tourne hors du conteneur
    llm_model: str = "llama3.1:8b"  # contrainte du sujet : modèle <= 8B paramètres
    embed_model: str = "nomic-embed-text"
    corpus_path: str = "/corpus"  # monté en lecture seule
    top_k: int = 8
    max_question_chars: int = 1000
    chunk_size: int = 800
    chunk_overlap: int = 100
    llm_timeout_s: float = 120.0  # un 8B sur CPU répond en dizaines de secondes

    @classmethod
    def from_env(cls) -> Settings:
        token = os.environ["RAG_TOKEN"]
        if not token:
            raise ValueError("RAG_TOKEN ne doit pas être vide")
        return cls(
            rag_token=token,
            ollama_url=os.environ.get("OLLAMA_URL", cls.ollama_url),
            llm_model=os.environ.get("LLM_MODEL", cls.llm_model),
            embed_model=os.environ.get("EMBED_MODEL", cls.embed_model),
            corpus_path=os.environ.get("CORPUS_PATH", cls.corpus_path),
            top_k=int(os.environ.get("TOP_K", cls.top_k)),
            max_question_chars=int(os.environ.get("MAX_QUESTION_CHARS", cls.max_question_chars)),
            chunk_size=int(os.environ.get("CHUNK_SIZE", cls.chunk_size)),
            chunk_overlap=int(os.environ.get("CHUNK_OVERLAP", cls.chunk_overlap)),
            llm_timeout_s=float(os.environ.get("LLM_TIMEOUT_S", cls.llm_timeout_s)),
        )
