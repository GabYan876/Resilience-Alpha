"""Similarité cosinus entre deux gabarits (règle pure, testable sans I/O)."""

from __future__ import annotations

import math

from app.domain.ports import Embedding


def cosine(a: Embedding, b: Embedding) -> float:
    if len(a) != len(b):
        return -1.0
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0:
        return -1.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm
