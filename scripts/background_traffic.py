#!/usr/bin/env python3
"""Trafic de fond NORMAL : sert à constituer le jeu de données d'entraînement du détecteur ML.

Rejoue des clients fictifs (Alice et Bob du seed) à travers la passerelle publiée, comme le
ferait le front : connexion, consultation du solde, historique, petits virements entre eux.
Le débit alterne des phases calmes, normales et chargées, car le modèle doit connaître toute
l'étendue du trafic légitime : sinon une journée chargée serait prise pour une attaque.

Ce n'est PAS un outil d'attaque : le débit reste volontairement modéré (voir `PHASES`).
Bibliothèque standard seule, pour tourner sur n'importe quel poste sans installation.

    python scripts/background_traffic.py --duration 900
"""

from __future__ import annotations

import argparse
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

# (nom, débit min, débit max en requêtes/s, durée min, durée max en s)
PHASES = (
    ("calme", 0.5, 2.0, 20, 45),
    ("normale", 3.0, 8.0, 30, 90),
    ("chargée", 10.0, 18.0, 15, 40),
)
PHASE_WEIGHTS = (2, 4, 1)  # la charge forte reste l'exception

USERS = ("alice@resilience.local", "bob@resilience.local")
WORKERS = 8
TIMEOUT_S = 5.0


@dataclass
class Session:
    email: str
    token: str = ""
    iban: str = ""


class Counters:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.ok = 0
        self.errors = 0

    def add(self, success: bool) -> None:
        with self._lock:
            if success:
                self.ok += 1
            else:
                self.errors += 1

    def snapshot(self) -> tuple[int, int]:
        with self._lock:
            return self.ok, self.errors


def call(
    base_url: str, method: str, path: str, token: str = "", body: dict | None = None
) -> tuple[int, dict | list | None]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base_url + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return response.status, json.loads(response.read() or "null")
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, None


def login(base_url: str, session: Session, password: str) -> bool:
    status, payload = call(
        base_url,
        "POST",
        "/auth/login",
        body={"email": session.email, "password": password},
    )
    if status != 200 or not isinstance(payload, dict):
        return False
    session.token = payload["token"]
    session.iban = payload["resp"]["iban"]
    return True


def one_action(base_url: str, session: Session, peer: Session, password: str) -> bool:
    """Un geste de client : 50 % solde, 35 % historique, 15 % virement."""
    if not session.token and not login(base_url, session, password):
        return False
    roll = random.random()
    if roll < 0.50:
        status, _ = call(base_url, "GET", "/me/account", session.token)
    elif roll < 0.85:
        status, _ = call(base_url, "GET", "/me/transactions?limit=20", session.token)
    else:
        status, _ = call(
            base_url,
            "POST",
            "/me/transfers",
            session.token,
            {
                "to_account": peer.iban,
                "amount_cents": random.randint(100, 500),
                "idempotency_key": uuid.uuid4().hex,
            },
        )
    if status == 401:  # jeton expiré : on se reconnecte au prochain geste
        session.token = ""
    return 200 <= status < 300


def run(base_url: str, password: str, duration_s: float | None) -> None:
    sessions = [Session(email) for email in USERS]
    if not all(login(base_url, s, password) for s in sessions):
        raise SystemExit(
            f"connexion impossible sur {base_url} : pile démarrée et seed_demo.py lancé ?"
        )

    counters = Counters()
    stop_at = None if duration_s is None else time.monotonic() + duration_s
    last_report = time.monotonic()

    def task() -> None:
        index = random.randrange(len(sessions))
        counters.add(
            one_action(base_url, sessions[index], sessions[1 - index], password)
        )

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        while stop_at is None or time.monotonic() < stop_at:
            name, low, high, min_s, max_s = random.choices(PHASES, PHASE_WEIGHTS)[0]
            rate = random.uniform(low, high)
            phase_end = time.monotonic() + random.uniform(min_s, max_s)
            print(f"phase {name} : ~{rate:.1f} req/s", flush=True)
            while time.monotonic() < phase_end and (
                stop_at is None or time.monotonic() < stop_at
            ):
                pool.submit(task)
                time.sleep(
                    random.expovariate(rate)
                )  # arrivées de Poisson : débit irrégulier
                if time.monotonic() - last_report >= 10:
                    ok, errors = counters.snapshot()
                    print(f"  {ok} ok, {errors} erreurs", flush=True)
                    last_report = time.monotonic()
    ok, errors = counters.snapshot()
    print(f"terminé : {ok} ok, {errors} erreurs")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument(
        "--duration", type=float, help="secondes ; sans valeur, jusqu'à Ctrl+C"
    )
    args = parser.parse_args()
    password = os.environ.get("SEED_PASSWORD", "demo-only-not-a-secret")
    try:
        run(args.base_url.rstrip("/"), password, args.duration)
    except KeyboardInterrupt:
        print("\narrêt demandé")


if __name__ == "__main__":
    main()
