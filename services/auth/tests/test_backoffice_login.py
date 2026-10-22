"""Machine à états de la connexion back-office, avec des doubles (aucune caméra, aucune LED)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.adapters.memory_stores import (
    InMemoryAccessJournal,
    InMemoryFaceSessionStore,
    InMemoryLockoutStore,
    InMemoryRoleStore,
)
from app.application.backoffice_login import BackOfficeLogin
from app.domain.errors import (
    AccountLocked,
    FaceCheckUnavailable,
    FaceNotRecognized,
    FaceNotVerified,
    InvalidCredentials,
    NotAuthorized,
)
from app.domain.models import LedMode, NewUser, Role
from tests.fakes import (
    FakeCamera,
    FakeClock,
    FakeFaceVerifier,
    InMemoryUserRepository,
    PlainHasher,
    RecordingLed,
    RecordingPublisher,
    StaticTokenIssuer,
)

ADMIN = "admin@resilience.test"


class Env:
    def __init__(self, *, camera_broken: bool = False, agent_broken: bool = False) -> None:
        self.users = InMemoryUserRepository()
        self.camera = FakeCamera(broken=camera_broken)
        self.faces = FakeFaceVerifier({ADMIN}, broken=agent_broken)
        self.led = RecordingLed()
        self.clock = FakeClock()
        self.publisher = RecordingPublisher()
        self.roles = InMemoryRoleStore({ADMIN: Role.ADMIN})
        self.journal = InMemoryAccessJournal()
        self.lockouts = InMemoryLockoutStore()
        self.login = BackOfficeLogin(
            self.users,
            PlainHasher(),
            StaticTokenIssuer(),
            self.camera,
            self.faces,
            self.led,
            self.lockouts,
            InMemoryFaceSessionStore(),
            self.clock,
            self.publisher,
            self.roles,
            self.journal,
        )

    async def seed(self) -> None:
        await self.users.create(
            NewUser("Admin", ADMIN, "0600000000", PlainHasher().hash("bon-mdp")), 0
        )


async def _env(**kwargs: bool) -> Env:
    env = Env(**kwargs)
    await env.seed()
    return env


@pytest.mark.anyio
async def test_visage_reconnu_puis_mot_de_passe_valide_donne_acces() -> None:
    env = await _env()
    await env.login.start(ADMIN)
    assert env.led.modes == [LedMode.OFF, LedMode.GREEN_BLINK]
    assert not env.camera.is_on

    result = await env.login.submit_password(ADMIN, "bon-mdp")

    assert result.token.startswith("admin-")
    assert env.led.modes[-1] == LedMode.GREEN_SOLID


@pytest.mark.anyio
async def test_visage_non_reconnu_rouge_fixe_camera_eteinte() -> None:
    env = await _env()
    env.faces.present = False

    with pytest.raises(FaceNotRecognized):
        await env.login.start(ADMIN)

    assert env.led.modes[-1] == LedMode.RED_SOLID
    assert not env.camera.is_on


@pytest.mark.anyio
async def test_mot_de_passe_sans_visage_refuse() -> None:
    env = await _env()

    with pytest.raises(FaceNotVerified):
        await env.login.submit_password(ADMIN, "bon-mdp")


@pytest.mark.anyio
async def test_reconnaissance_a_usage_unique() -> None:
    env = await _env()
    await env.login.start(ADMIN)
    await env.login.submit_password(ADMIN, "bon-mdp")

    with pytest.raises(FaceNotVerified):
        await env.login.submit_password(ADMIN, "bon-mdp")


@pytest.mark.anyio
async def test_reconnaissance_expiree_refusee() -> None:
    env = await _env()
    await env.login.start(ADMIN)
    env.clock.advance(timedelta(minutes=3))

    with pytest.raises(FaceNotVerified):
        await env.login.submit_password(ADMIN, "bon-mdp")


@pytest.mark.anyio
async def test_mauvais_mot_de_passe_rouge_clignotant_et_reprise_complete() -> None:
    env = await _env()
    await env.login.start(ADMIN)

    with pytest.raises(InvalidCredentials):
        await env.login.submit_password(ADMIN, "mauvais")

    assert env.led.modes[-1] == LedMode.RED_BLINK
    with pytest.raises(FaceNotVerified):  # tout recommencer par le visage
        await env.login.submit_password(ADMIN, "bon-mdp")


@pytest.mark.anyio
async def test_deux_echecs_bloquent_cinq_minutes_puis_liberent() -> None:
    env = await _env()
    env.faces.present = False
    with pytest.raises(FaceNotRecognized):
        await env.login.start(ADMIN)
    with pytest.raises(FaceNotRecognized):
        await env.login.start(ADMIN)

    with pytest.raises(AccountLocked) as locked:
        await env.login.start(ADMIN)
    assert 0 < locked.value.retry_after_seconds <= 301

    env.clock.advance(timedelta(minutes=5, seconds=1))
    env.faces.present = True
    await env.login.start(ADMIN)  # le compteur est reparti à 0


@pytest.mark.anyio
async def test_echec_visage_puis_mot_de_passe_faux_compte_comme_deux_echecs() -> None:
    env = await _env()
    env.faces.present = False
    with pytest.raises(FaceNotRecognized):
        await env.login.start(ADMIN)
    env.faces.present = True
    await env.login.start(ADMIN)
    with pytest.raises(InvalidCredentials):
        await env.login.submit_password(ADMIN, "mauvais")

    with pytest.raises(AccountLocked):
        await env.login.start(ADMIN)


@pytest.mark.anyio
async def test_succes_remet_le_compteur_a_zero() -> None:
    env = await _env()
    env.faces.present = False
    with pytest.raises(FaceNotRecognized):
        await env.login.start(ADMIN)
    env.faces.present = True
    await env.login.start(ADMIN)
    await env.login.submit_password(ADMIN, "bon-mdp")

    env.faces.present = False
    with pytest.raises(FaceNotRecognized):  # 1er échec d'une nouvelle série, pas de blocage
        await env.login.start(ADMIN)


@pytest.mark.anyio
async def test_identifiant_non_enrole_traite_comme_visage_non_reconnu() -> None:
    env = await _env()

    with pytest.raises(FaceNotRecognized):
        await env.login.start("inconnu@resilience.test")


@pytest.mark.anyio
@pytest.mark.parametrize("kwargs", [{"camera_broken": True}, {"agent_broken": True}])
async def test_echec_ferme_si_camera_ou_agent_en_panne(kwargs: dict[str, bool]) -> None:
    env = await _env(**kwargs)

    with pytest.raises(FaceCheckUnavailable):
        await env.login.start(ADMIN)
    with pytest.raises(FaceNotVerified):  # pas de repli sur le mot de passe seul
        await env.login.submit_password(ADMIN, "bon-mdp")
    assert not env.camera.is_on


@pytest.mark.anyio
async def test_led_en_panne_ne_bloque_pas_l_acces_et_est_journalisee() -> None:
    env = await _env()
    env.led.broken = True

    await env.login.start(ADMIN)
    await env.login.submit_password(ADMIN, "bon-mdp")

    assert any(name == "auth.led.unavailable" for name, _ in env.publisher.events)


@pytest.mark.anyio
async def test_journal_sans_identifiant_en_clair() -> None:
    env = await _env()
    await env.login.start(ADMIN)

    assert env.publisher.events
    assert all(ADMIN not in str(data) for _, data in env.publisher.events)


@pytest.mark.anyio
async def test_compte_sans_habilitation_refuse_sans_compter_d_echec() -> None:
    env = await _env()
    await env.roles.revoke(ADMIN)
    await env.login.start(ADMIN)

    with pytest.raises(NotAuthorized):
        await env.login.submit_password(ADMIN, "bon-mdp")

    assert env.led.modes[-1] is LedMode.RED_SOLID
    assert (await env.lockouts.get(ADMIN)).failures == 0
    assert any(name == "auth.access.denied_no_role" for name, _ in env.publisher.events)


@pytest.mark.anyio
async def test_succes_renvoie_le_role_et_un_jeton_de_back_office() -> None:
    env = await _env()
    await env.login.start(ADMIN)

    session = await env.login.submit_password(ADMIN, "bon-mdp")

    assert session.role is Role.ADMIN and session.token == f"admin-{ADMIN}"


@pytest.mark.anyio
async def test_journal_du_back_office_garde_l_identifiant_lisible() -> None:
    env = await _env()
    await env.login.start(ADMIN)
    await env.login.submit_password(ADMIN, "bon-mdp")

    events = [(e.event, e.identifier) for e in await env.journal.recent(10)]

    assert events[:2] == [("auth.login.succeeded", ADMIN), ("auth.face.recognized", ADMIN)]
