import io
import json

from app.adapters.json_publisher import JsonStdoutPublisher
from app.domain.models import PipelineEvent


def test_publishes_one_structured_json_line():
    stream = io.StringIO()
    JsonStdoutPublisher(stream).publish(
        PipelineEvent(event="incident.detected", trace_id="t1", incident_id="i1", data={"a": 1})
    )
    lines = stream.getvalue().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["service"] == "remediation"
    assert record["trace_id"] == "t1"
    assert record["event"] == "incident.detected"
    assert record["data"] == {"a": 1}
