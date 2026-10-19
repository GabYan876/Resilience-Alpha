# Environnement de développement

Mise en place du poste pour contribuer au dépôt. À faire une fois par PC.

## 1. Prérequis

| Outil | Version visée | Vérification |
|---|---|---|
| Docker Engine + Compose | Docker ≥ 28, Compose ≥ v2.30 | `docker --version && docker compose version` |
| Python | 3.11 à 3.13 pour les environnements locaux ; les images utilisent `python:3.12-slim` | `python3 --version` |
| Node.js | 20 LTS (front React) | `node --version` |
| Git | ≥ 2.40 | `git --version` |

Python 3.14 fonctionne pour lire le code, mais certaines roues binaires (`asyncpg`, `greenlet`) sont encore
irrégulières dessus. Les conteneurs sont la référence : si un test passe dans l'image et pas en local,
c'est l'image qui compte.

## 2. Secrets (SOPS + age)

Aucun secret en clair dans le dépôt. Les valeurs chiffrées vivent dans `infra/secrets/*.enc.yaml`,
la clé privée reste sur le poste.

```bash
# une seule fois par poste
age-keygen -o ~/.config/sops/age/keys.txt    # clé privée : JAMAIS dans le dépôt
grep 'public key' ~/.config/sops/age/keys.txt
```

Envoyer la ligne `public key` à Hugo, qui ajoute la clé dans `.sops.yaml` et re-chiffre les secrets.
Ensuite, pour déployer :

```bash
sops exec-env infra/secrets/dev.enc.yaml \
  'docker compose -f infra/compose/docker-compose.yml up -d'
```

`age-keys.txt`, `*.keys.txt`, `.env` et `infra/secrets/*` non chiffrés sont déjà dans `.gitignore`.

## 3. Outillage Claude Code

Le dépôt versionne la configuration des agents pour que tout le monde obtienne le même comportement :
`.claude/settings.json` (plugins et hooks) et `.mcp.json` (serveurs MCP).

| Outil | Type | Rôle |
|---|---|---|
| `rtk` | hook `PreToolUse` sur Bash | condense la sortie des commandes : moins de tokens, mêmes signaux |
| caveman | plugin, `JuliusBrussee/caveman` | réponses courtes, substance technique intégralement conservée |
| ponytail | plugin, `DietrichGebert/ponytail` | interdit le code superflu : vérifier l'existant et la bibliothèque standard avant d'écrire |
| context7 | serveur MCP (HTTP) | documentation à jour des bibliothèques (FastAPI, SQLAlchemy, Alembic, Grafana, Loki) |

### Installation

```bash
# plugins (depuis une session Claude Code, à la racine du dépôt)
/plugin marketplace add JuliusBrussee/caveman
/plugin marketplace add DietrichGebert/ponytail
/plugin            # vérifier que caveman et ponytail sont « enabled »

# rtk (optionnel, condensation de sortie)
# binaire attendu dans le PATH, par exemple ~/.local/bin/rtk
rtk --version
```

Le hook `rtk` est protégé par `command -v rtk` : un poste sans `rtk` fonctionne normalement,
la sortie des commandes est simplement complète au lieu d'être condensée.

context7 est interrogé sans clé par défaut (quotas limités). Pour lever les quotas, exporter la clé
dans le profil shell — **pas** dans `.env`, qui est réservé au runtime des conteneurs :

```bash
echo 'export CONTEXT7_API_KEY=...' >> ~/.bashrc
```

### Règles d'usage

Les règles d'usage — context7 et données sensibles, passerelles LLM tierces, réflexe anti-code-superflu —
sont dans [`CLAUDE.md`](../CLAUDE.md), section « Outillage Claude Code ». Elles ne sont pas recopiées ici :
une seule source de vérité, sinon les deux fichiers divergent.

Deux points qui ne concernent que le poste :

- caveman et ponytail sont des projets indépendants, non affiliés à Anthropic.
- Tout code généré par un agent doit rester compris et explicable par son auteur devant le jury. Un agent
  qui produit du code que personne ne sait défendre est une dette, pas un gain.

### Dépannage

- `caveman @ caveman (project)` affiche « The packages it lists were not installed, because it uses a
  yarn or pnpm lockfile » : avertissement cosmétique, à ignorer. Le dépôt embarque un `pnpm-lock.yaml`
  que l'installeur de plugins ne sait pas traiter, mais les hooks du plugin lancent `node` directement
  sur ses fichiers sans passer par `node_modules`. La voix et les compétences locales fonctionnent.
  Seules les compétences Caveman Cloud (`caveman-setup`, `caveman-learn`, `caveman-stats`,
  `caveman-discover`, `caveman-optimize`, `caveman-manage`) ont besoin du paquet manquant — et elles
  sont hors périmètre ici, car elles font transiter les requêtes LLM par une passerelle tierce.
- `/ponytail` ne change rien : le plugin expose à la fois une compétence et des hooks ; selon la version,
  la commande peut se router vers la compétence sans activer le hook. Vérifier avec `/plugin`, et relancer
  la session après activation.
- Un serveur MCP apparaît « failed to connect » : `/mcp` affiche l'erreur. Pour context7, vérifier l'accès
  réseau sortant vers `mcp.context7.com`.
- Pour réinitialiser les réglages personnels sans toucher à ceux de l'équipe, éditer
  `.claude/settings.local.json` (ignoré par Git) et non `.claude/settings.json`.

## 4. Vérification du poste

```bash
pytest services/                                    # tests unitaires
docker compose -f infra/compose/docker-compose.yml config   # compose valide
./scripts/check_transaction.sh                      # API saine + transaction de test
```
