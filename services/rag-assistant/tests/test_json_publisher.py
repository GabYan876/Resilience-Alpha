import io
import json

from app.adapters.json_publisher import JsonStdoutPublisher
from app.domain.models import RagEvent


def test_one_json_line_per_event_with_loki_fields():
    stream = io.StringIO()
    JsonStdoutPublisher(stream).publish(RagEvent("rag.answered", "t1", {"sources": ["a.md"]}))

    record = json.loads(stream.getvalue())

    assert stream.getvalue().endswith("\n")
    assert record["service"] == "rag-assistant"
    assert record["trace_id"] == "t1"
    assert record["event"] == "rag.answered"
    assert record["data"] == {"sources": ["a.md"]}
    assert "at" in record
