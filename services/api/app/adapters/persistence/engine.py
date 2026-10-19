"""Moteur et fabrique de sessions asynchrones (asyncpg)."""

from __future__ import annotations

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str, *, echo: bool = False, pool_size: int = 5) -> AsyncEngine:
    """`database_url` doit être de la forme `postgresql+asyncpg://...`.

    Attention : asyncpg ne connaît pas `sslmode` (option libpq) mais `ssl`.
    """
    # `reset_demo.sh` joue `downgrade base` puis `upgrade head` : tables et types
    # ENUM sont supprimés puis recréés sous le pool encore ouvert, ce qui invalide
    # les requêtes préparées en cache. Sans désactivation, la première transaction
    # après chaque reset échoue en InvalidCachedStatementError — éliminatoire pour
    # une démo rejouable sans intervention humaine. Deux caches à neutraliser :
    # celui du dialecte SQLAlchemy (paramètre d'URL) et celui d'asyncpg.
    url = make_url(database_url).update_query_dict(
        {"prepared_statement_cache_size": "0"}, append=False
    )
    return create_async_engine(
        url,
        connect_args={"statement_cache_size": 0},
        echo=echo,
        pool_size=pool_size,
        max_overflow=2,  # RAM limitée à 256 Mo : on garde le pool petit
        pool_pre_ping=True,  # un redémarrage de PostgreSQL ne doit pas tuer l'API
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
