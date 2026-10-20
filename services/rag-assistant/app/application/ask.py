"""Cas d'usage : répondre à une question à partir des seuls documents indexés."""

from __future__ import annotations

from app.application.indexing import IndexingService
from app.domain.models import Answer, AssistantUnavailable, InvalidQuestion, RagEvent
from app.domain.ports import AnswerGenerator, EventPublisher, PassageRetriever

NO_ANSWER = "Je n'ai trouvé aucune information dans les documents indexés."


class AskService:
    def __init__(
        self,
        indexing: IndexingService,
        retriever: PassageRetriever,
        generator: AnswerGenerator,
        publisher: EventPublisher,
        top_k: int = 4,
        max_question_chars: int = 1000,
    ) -> None:
        self._indexing = indexing
        self._retriever = retriever
        self._generator = generator
        self._publisher = publisher
        self._top_k = top_k
        self._max_question_chars = max_question_chars

    def ask(self, question: str, trace_id: str) -> Answer:
        question = question.strip()
        if not question:
            raise InvalidQuestion("question vide")
        if len(question) > self._max_question_chars:
            raise InvalidQuestion(f"question trop longue (max {self._max_question_chars})")

        # Le texte de la question n'est jamais journalisé : il pourrait contenir un secret.
        self._publisher.publish(RagEvent("rag.question", trace_id, {"chars": len(question)}))
        try:
            self._indexing.ensure_indexed(trace_id)
            passages = self._retriever.search(question, self._top_k)
            if not passages:
                answer = Answer(NO_ANSWER, ())
            else:
                text = self._generator.generate(question, passages)
                answer = Answer(text, tuple(dict.fromkeys(p.source for p in passages)))
        except AssistantUnavailable:
            self._publisher.publish(RagEvent("rag.failed", trace_id))
            raise
        self._publisher.publish(
            RagEvent("rag.answered", trace_id, {"sources": list(answer.sources)})
        )
        return answer
