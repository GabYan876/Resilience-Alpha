import pytest

from app.application.ask import NO_ANSWER, AskService
from app.application.indexing import IndexingService
from app.domain.models import AssistantUnavailable, Document, InvalidQuestion
from tests.fakes import FakeGenerator, FakeIndex, FakeSource, RecordingPublisher

DOCS = [
    Document("docs/a.md", "alpha"),
    Document("docs/a.md", "alpha bis"),
    Document("docs/b.md", "beta"),
]


def make(docs=DOCS, index_fail=False, generator_fail=False, max_chars=50):
    index, generator, publisher = (
        FakeIndex(index_fail),
        FakeGenerator(generator_fail),
        RecordingPublisher(),
    )
    indexing = IndexingService(FakeSource(docs), index, publisher)
    service = AskService(
        indexing, index, generator, publisher, top_k=3, max_question_chars=max_chars
    )
    return service, generator, publisher


def test_answer_cites_each_source_once_in_order():
    service, generator, publisher = make()
    answer = service.ask("  Qui ?  ", "t1")
    assert answer.text == "réponse à : Qui ?"
    assert answer.sources == ("docs/a.md", "docs/b.md")
    assert publisher.names == ["rag.question", "rag.indexed", "rag.answered"]


def test_question_text_is_never_logged():
    service, _, publisher = make()
    service.ask("mon mot de passe est hunter2", "t1")
    assert "hunter2" not in repr(publisher.events)


def test_no_passage_means_no_generation():
    service, generator, _ = make(docs=[])
    answer = service.ask("Qui ?", "t1")
    assert answer.text == NO_ANSWER
    assert answer.sources == ()
    assert generator.calls == []


@pytest.mark.parametrize("question", ["", "   ", "x" * 51])
def test_invalid_question_is_rejected_before_any_work(question):
    service, generator, publisher = make()
    with pytest.raises(InvalidQuestion):
        service.ask(question, "t1")
    assert publisher.events == []


def test_generator_failure_is_published():
    service, _, publisher = make(generator_fail=True)
    with pytest.raises(AssistantUnavailable):
        service.ask("Qui ?", "t1")
    assert publisher.names[-1] == "rag.failed"


def test_index_failure_propagates():
    service, _, publisher = make(index_fail=True)
    with pytest.raises(AssistantUnavailable):
        service.ask("Qui ?", "t1")
    assert publisher.names == ["rag.question", "rag.index_failed", "rag.failed"]
