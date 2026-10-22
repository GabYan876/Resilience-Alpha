"""Cas d'usage d'administration du back-office, avec des doubles (aucune I/O)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.adapters.memory_stores import (
    InMemoryAccessJournal,
    InMemoryLockoutStore,
    InMemoryRoleStore,
)
from app.application.backoffice_admin import BackOfficeAdmin
from app.domain.errors import CannotRevokeSelf, NotAuthorized, UnknownUser
from app.domain.models import LockoutRecord, NewUser, Role
from tests.fakes import FakeClock, InMemoryUserRepository, RecordingPublisher

ADMIN = "admin@resilience.test"
OPERATOR = "ops@resilience.test"
ALICE = "alice@resilience.test"


class Env:
    def __init__(self) -> None:
        self.users = InMemoryUserRepository()
        self.roles = InMemoryRoleStore({ADMIN: Role.ADMIN, OPERATOR: Role.OPERATOR})
        self.lockouts = InMemoryLockoutStore()
        self.journal = InMemoryAccessJournal()
        self.clock = FakeClock()
        self.publisher = RecordingPublisher()
        self.admin = BackOfficeAdmin(
            self.users, self.roles, self.lockouts, self.journal, self.clock, self.publisher
        )

    async def seed(self) -> None:
        for i, email in enumerate((ADMIN, OPERATOR, ALICE)):
            await self.users.create(NewUser(email, email, f"060000000{i}", "h"), 0)


async def _env() -> Env:
    env = Env()
    await env.seed()
    return env


@pytest.mark.anyio
async def test_admin_habilite_un_compte_existant_et_journalise_l_auteur() -> None:
    env = await _env()

    await env.admin.grant(ADMIN, ALICE, Role.OPERATOR)

    assert await env.roles.get(ALICE) is Role.OPERATOR
    entry = (await env.journal.recent(1))[0]
    assert (entry.event, entry.identifier) == ("auth.admin.role_granted", ALICE)
    assert ADMIN in entry.detail


@pytest.mark.anyio
async def test_compte_inconnu_non_habilitable() -> None:
    env = await _env()

    with pytest.raises(UnknownUser):
        await env.admin.grant(ADMIN, "inconnu@resilience.test", Role.ADMIN)


@pytest.mark.anyio
async def test_operateur_ne_modifie_rien() -> None:
    env = await _env()

    assert await env.admin.whoami(OPERATOR) is Role.OPERATOR
    with pytest.raises(NotAuthorized):
        await env.admin.grant(OPERATOR, ALICE, Role.ADMIN)
    with pytest.raises(NotAuthorized):
        await env.admin.unlock(OPERATOR, ALICE)


@pytest.mark.anyio
async def test_sans_role_aucune_lecture() -> None:
    env = await _env()

    with pytest.raises(NotAuthorized):
        await env.admin.journal(ALICE)
    assert env.publisher.events[-1][0] == "auth.admin.forbidden"


@pytest.mark.anyio
async def test_retrait_immediat_et_pas_d_auto_retrait() -> None:
    env = await _env()

    with pytest.raises(CannotRevokeSelf):
        await env.admin.revoke(ADMIN, ADMIN)
    await env.admin.revoke(ADMIN, OPERATOR)

    with pytest.raises(NotAuthorized):  # son jeton est encore valide, mais plus son rôle
        await env.admin.whoami(OPERATOR)


@pytest.mark.anyio
async def test_deblocage_ne_liste_que_les_identifiants_bloques() -> None:
    env = await _env()
    now = env.clock.now()
    await env.lockouts.save(LockoutRecord(ALICE, 0, now + timedelta(minutes=5)))
    await env.lockouts.save(LockoutRecord(OPERATOR, 1, None))

    assert [r.identifier for r in await env.admin.lockouts(OPERATOR)] == [ALICE]
    await env.admin.unlock(ADMIN, ALICE)
    assert await env.admin.lockouts(ADMIN) == []


@pytest.mark.anyio
async def test_evenements_loki_sans_identifiant_en_clair() -> None:
    env = await _env()

    await env.admin.grant(ADMIN, ALICE, Role.OPERATOR)

    assert all(
        ALICE not in str(data) and ADMIN not in str(data) for _, data in env.publisher.events
    )
