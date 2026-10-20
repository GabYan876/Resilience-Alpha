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

# Les archives d'une démo précédente ne doivent pas servir de point de restauration :
# on les purge puis on prend une sauvegarde de l'état propre fraîchement semé.
echo "[reset] sauvegardes S4 : purge puis archive de l'état propre"
compose up -d --wait db-recovery
compose exec -T db-recovery sh -c 'rm -f /backups/backup-*.dump && python3 -c "
import os, urllib.request
req = urllib.request.Request(\"http://127.0.0.1:8001/backup\", method=\"POST\",
    headers={\"Authorization\": \"Bearer \" + os.environ[\"PROBE_TOKEN\"]})
urllib.request.urlopen(req, timeout=120)"'

# `up -d` ne touche pas un conteneur déjà sain : il faut le recréer. Sans ça, le
# pool garde des connexions authentifiées sous l'ancien OID des rôles `app_rw` /
# `app_ro`, que downgrade/upgrade vient de supprimer puis recréer, et la première
# transaction échoue en « permission denied ». Le `pool_pre_ping` ne le voit pas :
# son `SELECT 1` ne touche aucune table, donc aucun contrôle d'ACL.
echo "[reset] recréation de l'API et de l'authentification (pools de connexions remis à neuf)"
compose up -d --force-recreate --no-deps --wait api auth

# Les sources bloquées par la remédiation précédente doivent être libérées, sinon la démo
# suivante démarrerait avec l'attaquant déjà bloqué. Le WAF relit la liste à chaque requête.
echo "[reset] liste de blocage du WAF vidée"
compose exec -T remediation sh -c ': > /blocklist/blocked.txt'

echo "[reset] terminé : base rejouable"
