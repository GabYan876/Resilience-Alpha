#!/usr/bin/env bash
# Preuve de vie du socle : l'API répond ET une vraie transaction passe.
# Un conteneur qui redémarre ne prouve rien.
#
# L'API n'est pas publiée sur l'hôte (seul le WAF/front le sera) : la vérification
# est donc jouée depuis l'intérieur du réseau Docker, dans le conteneur `api`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/compose/docker-compose.yml}"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env}"
FROM_ACCOUNT="${FROM_ACCOUNT:-TEST-0001}"
TO_ACCOUNT="${TO_ACCOUNT:-TEST-0002}"
AMOUNT_CENTS="${AMOUNT_CENTS:-100}"

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

compose exec -T \
  -e FROM_ACCOUNT="${FROM_ACCOUNT}" \
  -e TO_ACCOUNT="${TO_ACCOUNT}" \
  -e AMOUNT_CENTS="${AMOUNT_CENTS}" \
  api python - <<'PY'
import json
import os
import sys
import uuid

import httpx

base = "http://localhost:8000"
token = os.environ.get("PROBE_TOKEN", "")
headers = {"Authorization": f"Bearer {token}"} if token else {}

with httpx.Client(timeout=5.0) as client:
    health = client.get(f"{base}/health", headers=headers)
    if not health.is_success:
        print(f"ECHEC santé : HTTP {health.status_code} {health.text}", file=sys.stderr)
        sys.exit(1)

    payload = {
        "from_account": os.environ["FROM_ACCOUNT"],
        "to_account": os.environ["TO_ACCOUNT"],
        "amount_cents": int(os.environ["AMOUNT_CENTS"]),
        "idempotency_key": f"check-{uuid.uuid4().hex}",
    }
    response = client.post(f"{base}/transactions", json=payload, headers=headers)

if not response.is_success:
    print(f"ECHEC transaction : HTTP {response.status_code} {response.text}", file=sys.stderr)
    sys.exit(2)

body = response.json()
if body.get("status") != "settled":
    print(f"ECHEC transaction non réglée : {json.dumps(body)}", file=sys.stderr)
    sys.exit(3)

print(f"OK santé + transaction {body['id']} réglée ({body['amount_cents']} centimes)")
PY
