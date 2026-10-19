"""Moteur SQLAlchemy asynchrone (asyncpg) et sonde de santé."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def build_engine(database_url: str) -> AsyncEngine:
    # Mêmes réglages que l'API : `reset_demo.sh` recrée tables et types ENUM sous un pool
    # ouvert, ce qui invaliderait les requêtes préparées en cache (deux caches à neutraliser).
    url = make_url(database_url).update_query_dict(
        {"prepared_statement_cache_size": "0"}, append=False
    )
    return create_async_engine(
        url,
        connect_args={"statement_cache_size": 0},
        pool_size=3,
        max_overflow=1,  # conteneur limité à 128 Mo
        pool_pre_ping=True,
    )


class SqlAlchemyHealthProbe:
    """Implémente le port `HealthProbe` : /health ne doit pas mentir sur la base."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ping(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            return False
        return True
