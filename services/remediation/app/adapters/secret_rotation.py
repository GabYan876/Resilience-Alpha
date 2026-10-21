"""Rotation du secret JWT via SOPS/age (voir `docs/gouvernance/06-pilotage-arbitrages.md`).

Portée volontairement restreinte : ce conteneur ne déchiffre que `jwt.enc.yaml`, jamais
`infra/secrets/app.enc.yaml` (mots de passe BDD, jeton Grafana...). La clé age montée ici
(`SOPS_AGE_KEY_FILE`) n'est recipient que de ce seul fichier — une compromission du moteur
n'expose donc que le JWT, pas le reste des secrets.

`auth` et `api` ne relisent `JWT_SECRET` qu'au démarrage (`config.py`) : la rotation écrit la
nouvelle valeur sur le volume partagé, puis `RestartServiceAction` relance les deux pour qu'ils
la relisent. Un simple `docker restart` suffit : le fichier vit sur un volume, pas dans
l'environnement figé par Compose à la création du conteneur.
"""

from __future__ import annotations

import secrets
import subprocess
from collections.abc import Callable

SopsRunner = Callable[[list[str]], None]


def run_sops(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True, timeout=10)


class SopsSecretRotator:
    def __init__(
        self,
        encrypted_path: str,
        live_secret_path: str,
        run: SopsRunner = run_sops,
    ) -> None:
        self._encrypted_path = encrypted_path
        self._live_secret_path = live_secret_path
        self._run = run

    def rotate(self, secret_name: str) -> None:
        new_value = secrets.token_urlsafe(48)
        self._run(["sops", "--set", f'["{secret_name}"] "{new_value}"', self._encrypted_path])
        with open(self._live_secret_path, "w", encoding="utf-8") as handle:
            handle.write(new_value)
