"""Unité de travail SQLAlchemy : une session = une transaction applicative."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.persistence.repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyTransactionRepository,
)


class SqlAlchemyUnitOfWork:
    """Implémente le port `UnitOfWork`.

    Réutilisable : chaque `async with` ouvre une session neuve et la referme.
    Sans `commit()` explicite, la sortie du bloc annule tout (sécurité par défaut).
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.accounts = SqlAlchemyAccountRepository(self._session)
        self.transactions = SqlAlchemyTransactionRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            await self.rollback()  # sans effet si commit() a déjà eu lieu
        finally:
            session, self._session = self._session, None
            if session is not None:
                await session.close()

    async def commit(self) -> None:
        await self._require_session().commit()

    async def rollback(self) -> None:
        await self._require_session().rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("unité de travail utilisée hors de son bloc `async with`")
        return self._session
