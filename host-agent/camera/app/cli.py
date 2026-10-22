"""Outils en ligne de commande exécutés sur le PC Hôte (jamais exposés par HTTP).

python -m app.cli genkey <fichier>        crée la clé de chiffrement des gabarits
python -m app.cli enroll <identifiant>    enrôle le visage devant la caméra (membre consentant)
python -m app.cli revoke <identifiant>    supprime le gabarit
python -m app.cli check <identifiant>     mesure la similarité d'une image avec le gabarit
"""

from __future__ import annotations

import sys
from pathlib import Path

from cryptography.fernet import Fernet

from app.config import Settings
from app.main import build_agent


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"genkey", "enroll", "revoke", "check"}:
        print(__doc__)
        return 2
    command, target = argv[1], argv[2]
    if command == "genkey":
        path = Path(target)
        if path.exists():
            print(
                "refus : le fichier existe déjà (écraser la clé rendrait les gabarits illisibles)"
            )
            return 1
        path.write_bytes(Fernet.generate_key())
        print(f"clé écrite dans {path} (hors Git ; à sauvegarder avec SOPS)")
        return 0

    agent = build_agent(Settings.from_env())
    if command == "revoke":
        agent.templates.delete(target)
        print("gabarit supprimé")
        return 0

    agent.start()
    try:
        if command == "enroll":
            agent.enroll(target)
            print("gabarit enregistré (chiffré)")
            return 0
        score = agent.measure(target)
        if score is None:
            print("pas de gabarit, ou pas exactement un visage devant la caméra")
            return 1
        print(f"similarité {score:.3f} (seuil {agent.threshold}) -> {score >= agent.threshold}")
        return 0
    finally:
        agent.stop()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
