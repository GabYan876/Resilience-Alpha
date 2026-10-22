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

# Agent caméra hôte (consigne additionnelle 1) : jeton partagé entre `auth` et l'agent, propre à
# ce poste, jamais versionné. Généré seulement s'il est vide ; host-agent/camera/run.ps1 le relit
# dans ce .env. URL par défaut : l'agent écoute sur le port 8765 du PC Hôte.
set_if_empty() {
  grep -q "^$1=." "${ENV_FILE}" && return 0
  if grep -q "^$1=" "${ENV_FILE}"; then sed -i "s|^$1=.*|$1=$2|" "${ENV_FILE}"; else echo "$1=$2" >> "${ENV_FILE}"; fi
}
set_if_empty HOST_AGENT_URL "http://host.docker.internal:8765"
set_if_empty HOST_AGENT_TOKEN "$(head -c 48 /dev/urandom | base64 | tr -d '/+=\n' | head -c 48)"

echo "Écrit : ${ENV_FILE}"
