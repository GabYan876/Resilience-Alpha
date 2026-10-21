"""Exécute la même vérification de reprise que le moteur de remédiation."""

from __future__ import annotations

import sys

import httpx

from app.adapters.api_probe import ApiTransactionProbe
from app.adapters.http_health import HttpHealthChecker
from app.config import Settings


def check_transaction(client: httpx.Client, settings: Settings) -> bool:
    health = HttpHealthChecker(client, {"api": settings.api_health_url})
    if not health.is_healthy("api"):
        print("ECHEC santé API", file=sys.stderr)
        return False

    probe = ApiTransactionProbe(
        client,
        settings.api_base_url,
        settings.probe_token,
        settings.probe_from_account,
        settings.probe_to_account,
        settings.probe_amount_cents,
    )
    if not probe.run():
        print("ECHEC transaction de test non réglée", file=sys.stderr)
        return False

    print(f"OK santé + transaction réglée ({settings.probe_amount_cents} centimes)")
    return True


def main() -> int:
    settings = Settings.from_env()
    with httpx.Client(timeout=settings.http_timeout_s) as client:
        return 0 if check_transaction(client, settings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
