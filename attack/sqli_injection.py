#!/usr/bin/env python3
"""Injection SQL minimale : scénario ER2 (compromission), par opposition au flood ER1.

Objectif de la preuve : des charges SQLi classiques envoyées à travers le WAF sur des
champs réels de l'API (email de connexion, IBAN de destinataire d'un virement) sont
bloquées par ModSecurity + OWASP CRS (HTTP 403) avant d'atteindre `auth`/`api`, et
tracées dans Loki/Grafana (SIEM). Ce script ne prouve pas une injection réussie contre
PostgreSQL (les requêtes y sont déjà paramétrées côté `services/auth` et `services/api` :
aucune concatenation de SQL) ; il prouve la détection/le blocage en périmètre, qui est
la ligne « Au moins une attaque de compromission (SQLi) est bloquée, visible dans le
SIEM/Grafana » des critères de sortie du jalon.

Portée volontairement limitée (voir `docs/validation-jalon-21-10.md` §5) : ce script
est la partie « attaque » de François. Le traitement complet de S2 (rotation de secrets,
investigation) n'est pas câblé dans le moteur de remédiation (`VaultSecretRotator`
reste à développer, voir `docs/gouvernance/02-pca-pra.md` §2) ; seul le blocage/la
trace WAF sont démontrés ici.

Garde-fous (identiques à `attack/flood_http.py`) :
  - cible par défaut = la passerelle locale de CE dépôt (127.0.0.1:8080) ;
  - toute autre cible doit être explicitement confirmée (--yes-i-know-the-target) ;
  - jamais le réseau du campus, d'un autre groupe, ni Internet (règle du dépôt).

Usage :
    python attack/sqli_injection.py
    python attack/sqli_injection.py --base-url http://192.168.137.1:8080 --yes-i-know-the-target
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_TARGET = "http://127.0.0.1:8080"
ALLOWED_HOSTS = {
    "127.0.0.1",
    "localhost",
    "192.168.137.1",  # PC Hôte du consortium (hotspot RESILIENCE-G<n>)
    "192.168.1.140",  # PC Hôte du consortium (box du binôme Kevin, réseau privé équivalent)
}
TIMEOUT_S = 5.0

# Charges classiques (OWASP CRS les reconnaît au paranoia level 1 par défaut du WAF).
SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1 --",
    "' UNION SELECT NULL,NULL,NULL--",
    "admin'--",
    "1; DROP TABLE accounts;--",
    "' AND SLEEP(5)--",
]


def _check_target(base_url: str, confirmed: bool) -> None:
    from urllib.parse import urlparse

    host = urlparse(base_url).hostname or ""
    if host not in ALLOWED_HOSTS and not confirmed:
        raise SystemExit(
            f"cible '{base_url}' hors de la passerelle locale attendue.\n"
            "Règle du dépôt : attaques uniquement depuis le PC Attaquant vers le PC "
            "Hôte du consortium, sur le réseau privé du binôme (hotspot ou box), "
            "jamais le campus ni Internet.\n"
            "Si c'est bien le PC Hôte visé depuis le PC Attaquant, ajouter "
            "--yes-i-know-the-target."
        )


def _post(
    base_url: str, path: str, body: dict, token: str | None = None
) -> tuple[int, str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        base_url + path, data=json.dumps(body).encode(), method="POST", headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return response.status, response.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return -1, str(exc)


def login(base_url: str, email: str, password: str) -> str | None:
    status, body = _post(
        base_url, "/auth/login", {"email": email, "password": password}
    )
    if status != 200:
        return None
    try:
        return str(json.loads(body)["token"])
    except (KeyError, json.JSONDecodeError):
        return None


def attack_login(base_url: str) -> list[tuple[str, int]]:
    """Charges dans le champ email de `/auth/login`, sans authentification préalable."""
    results = []
    for payload in SQLI_PAYLOADS:
        status, _ = _post(base_url, "/auth/login", {"email": payload, "password": "x"})
        results.append((payload, status))
    return results


def attack_transfer(base_url: str, token: str) -> list[tuple[str, int]]:
    """Charges dans `to_account` (IBAN du bénéficiaire) de `/me/transfers`, authentifié."""
    results = []
    for payload in SQLI_PAYLOADS:
        body = {
            "to_account": payload,
            "amount_cents": 100,
            "idempotency_key": "sqli-probe",
        }
        status, _ = _post(base_url, "/me/transfers", body, token=token)
        results.append((payload, status))
    return results


def report(label: str, results: list[tuple[str, int]]) -> None:
    print(f"\n{label}")
    blocked = sum(1 for _, status in results if status == 403)
    for payload, status in results:
        verdict = "bloqué (403)" if status == 403 else f"status={status}"
        print(f"  {payload!r:45} -> {verdict}")
    print(f"  {blocked}/{len(results)} bloquées par le WAF")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default=DEFAULT_TARGET)
    parser.add_argument(
        "--email",
        default="alice@resilience.local",
        help="compte valide du seed de démo, pour obtenir un jeton avant le second lot",
    )
    parser.add_argument("--password", default="demo-only-not-a-secret")
    parser.add_argument(
        "--yes-i-know-the-target",
        action="store_true",
        help="confirme une cible hors de la liste ALLOWED_HOSTS",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    _check_target(base_url, args.yes_i_know_the_target)

    print(f"injection SQL (ER2) contre {base_url}, à travers le WAF")
    report("1) /auth/login, champ email, sans jeton :", attack_login(base_url))

    token = login(base_url, args.email, args.password)
    if token is None:
        print(
            "\nPas de jeton valide (compte/mot de passe de seed introuvables) : le second lot "
            "(/me/transfers) est ignoré. Lancer scripts/seed_demo.py si besoin."
        )
        return
    report(
        "2) /me/transfers, champ to_account, avec jeton valide :",
        attack_transfer(base_url, token),
    )

    print(
        "\nPreuve attendue dans Loki/Grafana (dashboard `resilience-alpha`, panneau SIEM/WAF) : "
        "règles CRS SQLi déclenchées, requêtes 403, source = ce PC. Voir "
        "`docs/gouvernance/02-pca-pra.md` (scénario S2) pour la limite actuelle : le blocage est "
        "automatique, la rotation de secrets et l'investigation restent manuelles."
    )


if __name__ == "__main__":
    main()
