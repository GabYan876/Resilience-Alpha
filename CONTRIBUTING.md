# Contribuer — PROJECT RESILIENCE-ALPHA

Règles de travail de l'équipe. Les règles d'architecture et de sécurité détaillées sont dans [`CLAUDE.md`](CLAUDE.md).

## Branches et PR

- Une branche par fonctionnalité, créée depuis `main` : `feat/<sujet>`, `fix/<sujet>`, `docs/<sujet>`, `infra/<sujet>`, `test/<sujet>`.
- Pas de push direct sur `main` : tout passe par une PR.
- Le dépôt est privé sur une offre gratuite : GitHub ne permet pas de protéger `main`. La règle repose donc sur l'équipe et sur un hook local qui refuse le push direct. **À installer une fois par PC** (depuis Git Bash) : `./scripts/install-hooks.sh`. `git push --no-verify` contourne le hook : ne pas l'utiliser.
- Une PR relue par le tech lead (Kevin) avant fusion. Une PR = un sujet, petite et lisible.
- La PR décrit : le résumé, les points d'attention pour la relecture, ce qui est testé et ce qui ne l'est pas.
- Gel du code jeudi 22/10 à 17h : plus de fusion après.

## Commits

- [Conventional Commits](https://www.conventionalcommits.org/fr/) : `feat:`, `fix:`, `docs:`, `infra:`, `test:`, `chore:`.
- Message en **français** à l'impératif ou au participe, première ligne courte. Identifiants de code en **anglais**.
- **Aucun co-auteur** : pas de ligne `Co-Authored-By` ni autre trailer d'attribution.

## Code Python

- Typage complet. Formatage `ruff format` (compatible `black`), lint `ruff check`, tests `pytest`.
- Architecture en couches (`domain` / `application` / `adapters` / `api`), dépendances vers le domaine : voir `CLAUDE.md`.
- Un adaptateur = un fichier de tests. Le domaine est testé sans I/O (avec des fakes).
- Pas de logique métier dans les routes FastAPI ni dans les playbooks Ansible.
- Logs structurés JSON avec `service`, `trace_id`, `event`.

```bash
cd services/<service>
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt pytest ruff
.venv/Scripts/python -m ruff format . --exclude .venv
.venv/Scripts/python -m ruff check . --exclude .venv
.venv/Scripts/python -m pytest
```

## Sécurité

- **Aucun secret** dans le dépôt, les images, les logs ni le zip final : Vault ou SOPS. `.env` est ignoré, on fournit un `.env.example` avec des placeholders.
- **Données 100 % fictives.**
- Ne jamais envoyer de clé, de secret ni de document confidentiel à une IA.
- Attaques uniquement depuis le PC Attaquant vers le PC Hôte du consortium, sur un réseau privé du binôme (hotspot `192.168.137.1` ou box personnelle). Jamais le réseau du campus, un autre groupe ni Internet.
- Avant d'ajouter un composant : impact RAM (`mem_limit`), exposition réseau, droits requis.

## Compréhension du code

Tout code, y compris généré par une IA, doit être **compris et explicable** par son auteur devant le jury. Si tu ne peux pas l'expliquer, ne le fusionne pas.
