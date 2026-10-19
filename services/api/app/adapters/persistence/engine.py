"""Moteur et fabrique de sessions asynchrones (asyncpg)."""

from __future__ import annotations

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
    return create_async_engine(
        database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=2,  # RAM limitée à 256 Mo : on garde le pool petit
        pool_pre_ping=True,  # un redémarrage de PostgreSQL ne doit pas tuer l'API
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
