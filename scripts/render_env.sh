#!/usr/bin/env bash
# Déchiffre infra/secrets/app.enc.yaml et infra/secrets/jwt.enc.yaml (clé "ops") et les fusionne
# avec .env.example pour produire .env (ignoré par Git). Voir
# docs/gouvernance/06-pilotage-arbitrages.md (choix SOPS + age) et docs/dev.md.
#
# JWT_SECRET ici n'amorce que le premier démarrage : `auth`/`api` (app/config.py) préfèrent le
# fichier JWT_SECRET_FILE dès qu'une rotation l'a écrit sur le volume partagé. Après une rotation,
# cette valeur rendue dans .env n'est plus celle réellement utilisée par les conteneurs en cours.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_SECRETS="${REPO_ROOT}/infra/secrets/app.enc.yaml"
JWT_SECRETS="${REPO_ROOT}/infra/secrets/jwt.enc.yaml"
ENV_EXAMPLE="${REPO_ROOT}/.env.example"
ENV_FILE="${REPO_ROOT}/.env"

if [[ -z "${SOPS_AGE_KEY_FILE:-}" ]]; then
  echo "SOPS_AGE_KEY_FILE doit pointer vers la clé age \"ops\" (partagée hors dépôt)." >&2
  exit 1
fi

cp "${ENV_EXAMPLE}" "${ENV_FILE}"

render_into_env() {
  while IFS='=' read -r name value; do
    [[ -z "${name}" ]] && continue
    if grep -q "^${name}=" "${ENV_FILE}"; then
      sed -i "s|^${name}=.*|${name}=${value}|" "${ENV_FILE}"
    else
      echo "${name}=${value}" >> "${ENV_FILE}"
    fi
  done < <(sops --decrypt --output-type dotenv "$1")
}

render_into_env "${APP_SECRETS}"
render_into_env "${JWT_SECRETS}"

echo "Écrit : ${ENV_FILE}"
