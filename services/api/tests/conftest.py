"""Configuration pytest : les cas d'usage sont asynchrones, on utilise le greffon anyio."""

from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
