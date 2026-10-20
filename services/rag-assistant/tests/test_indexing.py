import pytest

from app.application.indexing import IndexingService
from app.domain.models import AssistantUnavailable, Document
from tests.fakes import FakeIndex, FakeSource, RecordingPublisher

DOCS = [Document("docs/a.md", "alpha"), Document("docs/b.md", "beta")]


def make(fail: bool = False):
    index, publisher = FakeIndex(fail), RecordingPublisher()
    return IndexingService(FakeSource(DOCS), index, publisher), index, publisher


def test_reindex_counts_and_publishes():
    service, _, publisher = make()
    assert service.reindex("t1") == 2
    assert service.chunk_count == 2
    assert publisher.names == ["rag.indexed"]
    assert publisher.events[0].data == {"documents": 2, "chunks": 2}


def test_ensure_indexed_runs_once():
    service, index, _ = make()
    service.ensure_indexed("t1")
    service.ensure_indexed("t2")
    assert index.index_calls == 1


def test_failure_is_published_and_retried_next_time():
    service, index, publisher = make(fail=True)
    with pytest.raises(AssistantUnavailable):
        service.ensure_indexed("t1")
    assert publisher.names == ["rag.index_failed"]
    assert service.chunk_count == 0

    index.fail = False
    service.ensure_indexed("t2")  # Ollama est revenu
    assert service.chunk_count == 2
