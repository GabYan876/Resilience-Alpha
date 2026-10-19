"""Routes /me : le jeton fixe l'identité, le corps ne peut pas désigner le compte source."""

from __future__ import annotations

import time
from uuid import UUID

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.jwt_verifier import JwtTokenVerifier
from app.api.me_routes import build_me_router
from app.application.transfer import ExecuteTransfer
from app.domain.models import Account
from tests.fakes import FakeUnitOfWork, InMemoryAccountRepository, RecordingPublisher

SECRET = "s" * 32


def _token(user_id: UUID, *, secret: str = SECRET, ttl: int = 60, alg: str = "HS256") -> str:
    now = int(time.time())
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + ttl}, secret, algorithm=alg)


def _setup() -> tuple[TestClient, Account, Account]:
    alice = Account(user_id=UUID(int=1), iban_fake="FR-ALICE", balance_cents=10_000)
    bob = Account(user_id=UUID(int=2), iban_fake="FR-BOB", balance_cents=500)
    uow = FakeUnitOfWork(InMemoryAccountRepository([alice, bob]))
    app = FastAPI()
    app.include_router(
        build_me_router(
            lambda: uow,
            lambda: ExecuteTransfer(uow, RecordingPublisher()),
            JwtTokenVerifier(SECRET),
        )
    )
    return TestClient(app, raise_server_exceptions=False), alice, bob


def _auth(user_id: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user_id)}"}


def test_sans_jeton_valide_401() -> None:
    client, alice, _ = _setup()

    assert client.get("/me/account").status_code == 401
    assert (
        client.get("/me/account", headers={"Authorization": "Bearer nimporte"}).status_code == 401
    )
    mauvais = {"Authorization": f"Bearer {_token(alice.user_id, secret='autre' * 8)}"}
    assert client.get("/me/account", headers=mauvais).status_code == 401
    expire = {"Authorization": f"Bearer {_token(alice.user_id, ttl=-5)}"}
    assert client.get("/me/account", headers=expire).status_code == 401


def test_jeton_alg_none_refuse() -> None:
    client, alice, _ = _setup()
    forge = jwt.encode({"sub": str(alice.user_id), "exp": int(time.time()) + 60}, None, "none")

    assert (
        client.get("/me/account", headers={"Authorization": f"Bearer {forge}"}).status_code == 401
    )


def test_solde_du_client() -> None:
    client, alice, _ = _setup()

    response = client.get("/me/account", headers=_auth(alice.user_id))

    assert response.status_code == 200
    assert response.json()["balance_cents"] == 10_000


def test_virement_debite_le_proprietaire_du_jeton_et_apparait_dans_l_historique() -> None:
    client, alice, bob = _setup()
    body = {"to_account": "FR-BOB", "amount_cents": 2_500, "idempotency_key": "cle-unique-1"}

    sent = client.post("/me/transfers", json=body, headers=_auth(alice.user_id))
    mine = client.get("/me/transactions", headers=_auth(alice.user_id)).json()
    theirs = client.get("/me/transactions", headers=_auth(bob.user_id)).json()

    assert sent.status_code == 200 and sent.json()["status"] == "settled"
    assert [(h["direction"], h["counterparty_iban"]) for h in mine] == [("debit", "FR-BOB")]
    assert [(h["direction"], h["counterparty_iban"]) for h in theirs] == [("credit", "FR-ALICE")]
    assert client.get("/me/account", headers=_auth(alice.user_id)).json()["balance_cents"] == 7_500


def test_le_corps_ne_peut_pas_choisir_le_compte_source() -> None:
    client, alice, bob = _setup()
    body = {
        "from_account": "FR-BOB",
        "to_account": "FR-ALICE",
        "amount_cents": 100,
        "idempotency_key": "cle-unique-2",
    }

    client.post("/me/transfers", json=body, headers=_auth(alice.user_id))

    assert client.get("/me/account", headers=_auth(bob.user_id)).json()["balance_cents"] == 500


def test_rejouer_la_meme_cle_ne_debite_qu_une_fois() -> None:
    client, alice, _ = _setup()
    body = {"to_account": "FR-BOB", "amount_cents": 1_000, "idempotency_key": "cle-unique-3"}

    first = client.post("/me/transfers", json=body, headers=_auth(alice.user_id))
    again = client.post("/me/transfers", json=body, headers=_auth(alice.user_id))

    assert first.json()["id"] == again.json()["id"]
    assert client.get("/me/account", headers=_auth(alice.user_id)).json()["balance_cents"] == 9_000


def test_la_cle_d_un_autre_client_ne_revele_pas_sa_transaction() -> None:
    client, alice, bob = _setup()
    body = {"to_account": "FR-ALICE", "amount_cents": 100, "idempotency_key": "cle-partagee"}
    client.post("/me/transfers", json=body, headers=_auth(bob.user_id))

    other = client.post(
        "/me/transfers", json={**body, "to_account": "FR-BOB"}, headers=_auth(alice.user_id)
    )

    assert other.json()["account_from"] == str(alice.id)


def test_solde_insuffisant_donne_409() -> None:
    client, alice, _ = _setup()
    body = {"to_account": "FR-BOB", "amount_cents": 999_999, "idempotency_key": "cle-unique-4"}

    response = client.post("/me/transfers", json=body, headers=_auth(alice.user_id))

    assert response.status_code == 409 and response.json()["status"] == "rejected"
