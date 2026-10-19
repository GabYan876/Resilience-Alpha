#!/usr/bin/env bash
# Remet la base dans un état identique à chaque passage : schéma reconstruit puis
# jeu de données fictif rechargé (dont le solde du compte de sonde).
# La démonstration doit pouvoir être rejouée au moins cinq fois sans intervention.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/infra/compose/docker-compose.yml}"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env}"
ALEMBIC="alembic -c /app/db/alembic.ini"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "fichier d'environnement absent : ${ENV_FILE} (copier .env.example)" >&2
  exit 1
fi

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

echo "[reset] démarrage de PostgreSQL"
compose up -d --wait postgres

# Le service `migrate` est le seul à détenir les droits DDL (rôle propriétaire).
echo "[reset] schéma : downgrade base puis upgrade head"
compose run --rm --no-deps --entrypoint sh migrate -c \
  "${ALEMBIC} downgrade base && ${ALEMBIC} upgrade head && python /app/scripts/seed_demo.py"

echo "[reset] redémarrage de l'API (pool de connexions remis à neuf)"
compose up -d --wait api

echo "[reset] terminé : base rejouable"
