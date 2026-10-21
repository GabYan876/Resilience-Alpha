"""Tests de la couche API : routage, codes HTTP, garde par jeton. Aucune base réelle."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import build_router
from app.application.transfer import ExecuteTransfer
from tests.fakes import (
    AlwaysDownProbe,
    AlwaysHealthyProbe,
    FakeUnitOfWork,
    InMemoryAccountRepository,
    RecordingPublisher,
    make_account,
)

PROBE_PAYLOAD = {
    "from_account": "TEST-0001",
    "to_account": "TEST-0002",
    "amount_cents": 100,
    "idempotency_key": "check-test",
}


def _client(
    *,
    balance_cents: int = 10_000,
    token: str = "",
    database_up: bool = True,
) -> tuple[TestClient, FakeUnitOfWork]:
    uow = FakeUnitOfWork(
        InMemoryAccountRepository(
            [make_account("TEST-0001", balance_cents), make_account("TEST-0002", 0)]
        )
    )
    transfer = ExecuteTransfer(uow, RecordingPublisher())
    app = FastAPI()
    app.include_router(
        build_router(
            lambda: uow,
            lambda: transfer,
            AlwaysHealthyProbe() if database_up else AlwaysDownProbe(),
            lambda: token,
        )
    )
    return TestClient(app, raise_server_exceptions=False), uow


def test_health_signale_une_base_saine() -> None:
    client, _ = _client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_health_ne_ment_pas_quand_la_base_est_injoignable() -> None:
    client, _ = _client(database_up=False)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["database"] == "down"


def test_la_charge_utile_de_la_sonde_de_remediation_est_acceptee() -> None:
    """Contrat avec `services/remediation` : montant en centimes et clé d'idempotence."""
    client, _ = _client()

    response = client.post("/transactions", json=PROBE_PAYLOAD)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "settled"
    assert body["amount_cents"] == 100


def test_montant_en_centimes_accepte() -> None:
    client, _ = _client()

    response = client.post(
        "/transactions",
        json={"from_account": "TEST-0001", "to_account": "TEST-0002", "amount_cents": 2_500},
    )

    assert response.status_code == 200
    assert response.json()["amount_cents"] == 2_500


def test_montant_en_unites_refuse() -> None:
    """L'ancien champ `amount` (unités) n'existe plus : `amount_cents` est obligatoire."""
    client, _ = _client()

    response = client.post(
        "/transactions",
        json={"from_account": "TEST-0001", "to_account": "TEST-0002", "amount": 1.0},
    )

    assert response.status_code == 422


def test_montant_en_centimes_non_entier_refuse() -> None:
    client, _ = _client()

    response = client.post(
        "/transactions",
        json={"from_account": "TEST-0001", "to_account": "TEST-0002", "amount_cents": 1.5},
    )

    assert response.status_code == 422


def test_solde_insuffisant_renvoie_409_et_non_un_succes() -> None:
    """La sonde de reprise ne doit jamais lire un refus comme une preuve de reprise."""
    client, _ = _client(balance_cents=50)

    response = client.post("/transactions", json=PROBE_PAYLOAD)

    assert response.status_code == 409
    assert response.json()["status"] == "rejected"


def test_compte_inconnu_renvoie_404() -> None:
    client, _ = _client()

    response = client.post(
        "/transactions",
        json={"from_account": "INCONNU", "to_account": "TEST-0002", "amount_cents": 100},
    )

    assert response.status_code == 404


def test_ecriture_sans_jeton_refusee_quand_la_garde_est_active() -> None:
    client, _ = _client(token="jeton-de-test")

    assert client.post("/transactions", json=PROBE_PAYLOAD).status_code == 401
    assert (
        client.post(
            "/transactions",
            json=PROBE_PAYLOAD,
            headers={"Authorization": "Bearer jeton-de-test"},
        ).status_code
        == 200
    )


def test_lecture_d_une_transaction() -> None:
    client, _ = _client()
    created = client.post("/transactions", json=PROBE_PAYLOAD).json()

    response = client.get(f"/transactions/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert client.get(f"/transactions/{'0' * 8}-0000-0000-0000-000000000000").status_code == 404


def test_lecture_du_solde_de_la_sonde() -> None:
    client, _ = _client()

    response = client.get("/accounts/TEST-0001")

    assert response.status_code == 200
    assert response.json()["balance_cents"] == 10_000
    assert client.get("/accounts/INCONNU").status_code == 404
