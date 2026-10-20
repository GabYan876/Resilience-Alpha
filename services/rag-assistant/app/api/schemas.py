from __future__ import annotations

from pydantic import BaseModel

from app.domain.models import Answer


class AskIn(BaseModel):
    question: str


class AskOut(BaseModel):
    answer: str
    sources: list[str]
    trace_id: str

    @classmethod
    def from_domain(cls, answer: Answer, trace_id: str) -> AskOut:
        return cls(answer=answer.text, sources=list(answer.sources), trace_id=trace_id)
