"""Cas d'usage et adaptateurs de sécurité, testés avec des doubles en mémoire."""

from __future__ import annotations

import jwt
import pytest

from app.adapters.security import Argon2PasswordHasher, JwtTokenIssuer
from app.application.use_cases import LoginUser, RegisterUser
from app.domain.errors import EmailAlreadyUsed, InvalidCredentials, PhoneAlreadyUsed
from tests.fakes import InMemoryUserRepository, PlainHasher, RecordingPublisher, StaticTokenIssuer


def _register(users: InMemoryUserRepository, publisher: RecordingPublisher) -> RegisterUser:
    return RegisterUser(users, PlainHasher(), StaticTokenIssuer(), publisher, 100_000)


async def _sign_up(use_case: RegisterUser, email: str = "a@b.fr", phone: str = "0612345678"):
    return await use_case.execute(full_name="A", email=email, phone=phone, password="pw-fictif-1")


@pytest.mark.anyio
async def test_inscription_credite_le_solde_de_bienvenue_et_stocke_un_hachage() -> None:
    users = InMemoryUserRepository()

    result = await _sign_up(_register(users, RecordingPublisher()))

    assert result.profile.balance_cents == 100_000
    assert users.by_email["a@b.fr"].password_hash == "hashed:pw-fictif-1"


@pytest.mark.anyio
async def test_doublons_email_et_telephone_refuses() -> None:
    users = InMemoryUserRepository()
    use_case = _register(users, RecordingPublisher())
    await _sign_up(use_case)

    with pytest.raises(EmailAlreadyUsed):
        await _sign_up(use_case, phone="0699999999")
    with pytest.raises(PhoneAlreadyUsed):
        await _sign_up(use_case, email="autre@b.fr")


@pytest.mark.anyio
async def test_connexion_refuse_email_inconnu_et_mauvais_mot_de_passe() -> None:
    users, publisher = InMemoryUserRepository(), RecordingPublisher()
    await _sign_up(_register(users, publisher))
    login = LoginUser(users, PlainHasher(), StaticTokenIssuer(), publisher)

    with pytest.raises(InvalidCredentials):
        await login.execute(email="inconnu@b.fr", password="pw-fictif-1")
    with pytest.raises(InvalidCredentials):
        await login.execute(email="a@b.fr", password="faux")
    assert [e for e, _ in publisher.events].count("auth.login_failed") == 2


def test_argon2_verifie_et_rejette() -> None:
    hasher = Argon2PasswordHasher()
    hashed = hasher.hash("secret-fictif")

    assert hasher.verify("secret-fictif", hashed)
    assert not hasher.verify("autre", hashed)
    assert not hasher.verify("secret-fictif", "pas-un-hachage")


def test_jwt_porte_sub_et_expire() -> None:
    from uuid import uuid4

    user_id = uuid4()
    token = JwtTokenIssuer("s" * 32, 60).issue(user_id)

    assert jwt.decode(token, "s" * 32, algorithms=["HS256"])["sub"] == str(user_id)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(JwtTokenIssuer("s" * 32, -10).issue(user_id), "s" * 32, algorithms=["HS256"])
