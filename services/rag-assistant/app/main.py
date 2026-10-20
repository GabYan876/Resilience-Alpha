"""Composition root : câble les adaptateurs aux ports (seul endroit qui les connaît)."""

from __future__ import annotations

import sys
import threading
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.adapters.json_publisher import JsonStdoutPublisher
from app.adapters.langchain_generator import LangChainAnswerGenerator
from app.adapters.langchain_index import LangChainPassageIndex
from app.adapters.markdown_corpus import MarkdownCorpus
from app.api.routes import build_router
from app.application.ask import AskService
from app.application.indexing import IndexingService
from app.config import Settings
from app.domain.models import AssistantUnavailable


def build_services(
    settings: Settings,
    embeddings: Embeddings | None = None,
    chat_model: BaseChatModel | None = None,
) -> tuple[IndexingService, AskService]:
    timeout = {"timeout": settings.llm_timeout_s}
    embeddings = embeddings or OllamaEmbeddings(
        model=settings.embed_model, base_url=settings.ollama_url, client_kwargs=timeout
    )
    chat_model = chat_model or ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_url,
        temperature=0,
        client_kwargs=timeout,
    )
    publisher = JsonStdoutPublisher(sys.stdout)
    index = LangChainPassageIndex(embeddings, settings.chunk_size, settings.chunk_overlap)
    indexing = IndexingService(MarkdownCorpus(Path(settings.corpus_path)), index, publisher)
    ask = AskService(
        indexing,
        index,
        LangChainAnswerGenerator(chat_model),
        publisher,
        top_k=settings.top_k,
        max_question_chars=settings.max_question_chars,
    )
    return indexing, ask


def create_app(
    settings: Settings | None = None,
    embeddings: Embeddings | None = None,
    chat_model: BaseChatModel | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    indexing, ask = build_services(settings, embeddings, chat_model)

    def warm_up() -> None:
        try:
            indexing.ensure_indexed(uuid.uuid4().hex)
        except AssistantUnavailable:
            pass  # déjà journalisé (rag.index_failed) ; la première question réessaiera

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # En arrière-plan : le démarrage (et son healthcheck) n'attend pas Ollama.
        threading.Thread(target=warm_up, daemon=True).start()
        yield

    app = FastAPI(title="rag-assistant", lifespan=lifespan)
    app.include_router(build_router(lambda: ask, lambda: indexing, lambda: settings.rag_token))
    return app
