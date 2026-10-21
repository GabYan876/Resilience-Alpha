#!/usr/bin/env bash
# Preuve de vie du socle : l'API répond ET une vraie transaction passe.
# Un conteneur qui redémarre ne prouve rien.
#
# L'API n'est pas publiée sur l'hôte (seul le WAF/front le sera) : la vérification
# est donc jouée depuis le conteneur de remédiation, avec la même sonde que le vérificateur.
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
  remediation python -m app.cli.check_transaction
