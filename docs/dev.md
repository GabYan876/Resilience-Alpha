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

Aucun secret en clair dans le dépôt (voir `06-pilotage-arbitrages.md` pour le choix SOPS plutôt que
Vault). Les valeurs chiffrées vivent dans `infra/secrets/*.enc.yaml` (`.sops.yaml` à la racine décrit
qui déchiffre quoi), la clé privée reste sur le poste et hors dépôt.

Deux clés age, deux périmètres (moindre privilège) :

- **"ops"** : déchiffre `infra/secrets/app.enc.yaml` (mots de passe BDD, jeton Grafana, `PROBE_TOKEN`...)
  et `infra/secrets/jwt.enc.yaml`. Clé privée partagée hors dépôt entre les 5 membres de l'équipe
  (demander à Kevin), jamais commitée.
- **"rotation"** : déchiffre seulement `infra/secrets/jwt.enc.yaml`. Sa clé privée est la seule montée
  dans le conteneur `remediation` — une compromission du moteur n'expose que le JWT, jamais les mots
  de passe BDD/Grafana.

Pour un poste de dev (déchiffrement avec la clé "ops") :

```bash
# une seule fois par poste, pour obtenir la clé "ops" auprès de Kevin
export SOPS_AGE_KEY_FILE=/chemin/vers/ops-age-key.txt

# produit .env (ignoré par Git) à partir de .env.example + les deux fichiers chiffrés
bash scripts/render_env.sh
```

`render_env.sh` copie `.env.example` vers `.env` puis y substitue chaque secret déchiffré. `.env` reste
réservé au runtime des conteneurs ; le relancer après toute rotation de secret ne resynchronise pas la
valeur réellement utilisée par `auth`/`api`, qui préfèrent le fichier `JWT_SECRET_FILE` dès qu'une
rotation a eu lieu (voir `services/remediation/app/adapters/secret_rotation.py`).

Pour ajouter ou modifier un secret : `sops infra/secrets/app.enc.yaml` (ou `jwt.enc.yaml`) ouvre un
éditeur sur le texte déchiffré et re-chiffre à la sauvegarde.

`*-age-key.txt`, `.env` et `infra/secrets/*` non chiffrés sont déjà dans `.gitignore`.

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

# rtk (optionnel, condensation de sortie) — https://github.com/rtk-ai/rtk
# binaire attendu dans le PATH, par exemple ~/.local/bin/rtk
rtk --version
```

### Versions épinglées des plugins

`.claude/settings.json` épingle chaque marketplace à un tag (`ref`), **sans `autoUpdate`** : du code tiers
ne doit pas se mettre à jour tout seul sur les 5 postes. Une montée de version est un acte volontaire,
relu, et committé.

| Marketplace | Tag épinglé | Commit résolu |
|---|---|---|
| `JuliusBrussee/caveman` | `v4.0.1` | `d262ab3882952a59312ff3537cd86d894523c5ab` |
| `DietrichGebert/ponytail` | `v5.3.2` | `16352ac229eb08a9598dcae48fe9f2b342567d86` |

Un tag Git peut être déplacé par son auteur. Vérifier que ce n'est pas arrivé :

```bash
git ls-remote --tags https://github.com/JuliusBrussee/caveman   refs/tags/v4.0.1^{}
git ls-remote --tags https://github.com/DietrichGebert/ponytail refs/tags/v5.3.2^{}
```

Les SHA affichés doivent correspondre au tableau. Pour changer de version : modifier le `ref`, relire le
diff amont, mettre à jour le tableau, et passer par une PR.

### Ce que ces outils exécutent

À connaître avant d'accepter la configuration : caveman et ponytail installent des hooks qui lancent
**`node` sur du code tiers**, à chaque démarrage de session et à chaque soumission de prompt. Le hook rtk
lance un binaire local avant chaque appel Bash. Ce code tourne sur un poste qui contient le dépôt, les
clés `age` et les secrets du projet.

Le hook `rtk` est protégé par `command -v rtk` : un poste sans `rtk` fonctionne normalement, la sortie des
commandes est simplement complète au lieu d'être condensée.

**rtk envoie de la télémétrie** à `https://telemetry.rtk-ai.app/ping` ; le suivi est actif par défaut
(`[tracking] enabled = true` dans `~/.config/rtk/config.toml`). Pour le couper :

```bash
rtk config          # inspecter la configuration courante
# puis passer [tracking] enabled = false dans ~/.config/rtk/config.toml
export RTK_DISABLED=1   # désactive rtk entièrement pour une session
```

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

## Ollama (assistant RAG)

Un seul Ollama suffit : seul le conteneur `rag-assistant` l'appelle. Il tourne sur un **PC Linux dédié**
(les commandes `systemd` et `ufw` ci-dessous valent pour ce poste ; sous Windows/Docker Desktop, il faudrait
adapter l'écoute et le pare-feu). Chacun peut aussi lancer le sien (défaut
`OLLAMA_URL=http://host.docker.internal:11434`) ou pointer vers celui d'un autre via `OLLAMA_URL`.
Ollama n'a aucune authentification et le hotspot est un réseau plat où se trouve aussi le PC
Attaquant : ne jamais le faire écouter sur `0.0.0.0`.

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
printf '[Service]\nEnvironment="OLLAMA_HOST=172.17.0.1:11434"\n' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama
OLLAMA_HOST=172.17.0.1:11434 ollama pull llama3.2:3b   # 3b pour valider, llama3.1:8b pour la démo
OLLAMA_HOST=172.17.0.1:11434 ollama pull nomic-embed-text
```

Sur un 3e PC, écouter sur son IP du hotspot et n'accepter que le PC hôte (`ufw allow from 192.168.137.1
to any port 11434 proto tcp`, puis `ufw deny 11434/tcp`).

**Partager son Ollama pour un test d'équipe** : écouter sur son IP du hotspot (`OLLAMA_HOST=<IP>:11434`),
autoriser **une règle `ufw allow from <IP du coéquipier>` par poste** (jamais `0.0.0.0` ni le sous-réseau
entier : le PC Attaquant y est aussi), puis le coéquipier met `OLLAMA_URL=http://<IP>:11434` dans son `.env`.
Retirer les règles après le test (`ufw status numbered`, `ufw delete <n>`). Le conteneur `rag-assistant` de
l'hôte n'a plus alors besoin que de cette URL ; un Ollama local n'est plus nécessaire.

## 4. Vérification du poste

Les tests se lancent **service par service** : chacun a ses propres dépendances et son propre
`pythonpath` dans son `pyproject.toml`. Un `pytest services/` depuis la racine échoue, les paquets `app`
des différents services entrant en collision.

```bash
# Un service à la fois, avec ses dépendances installées
cd services/api        && pip install -r requirements.txt && python -m pytest -q
cd services/remediation && pip install -r requirements.txt && python -m pytest -q
cd services/rag-assistant && pip install -r requirements.txt && python -m pytest -q

# Compose valide (le fichier lit .env, d'où --env-file)
docker compose --env-file .env -f infra/compose/docker-compose.yml config --quiet

# Preuve de vie : API saine + vraie transaction (pile démarrée au préalable)
docker compose --env-file .env -f infra/compose/docker-compose.yml up -d --wait --build
./scripts/check_transaction.sh
```

Le script vérifie la santé de l'API puis lance le CLI `app.cli.check_transaction` dans le
conteneur `remediation`. Celui-ci réutilise l'adaptateur `ApiTransactionProbe` aussi appelé par
le vérificateur de reprise ; les deux chemins exigent une transaction au statut `settled`.
Les comptes et le montant fictifs sont configurables avec `FROM_ACCOUNT`, `TO_ACCOUNT` et
`AMOUNT_CENTS`.

### Dépannage du démarrage de la pile

| Symptôme | Cause | Solution |
|---|---|---|
| `pull access denied for resilience-alpha/<service>, repository does not exist` | Les images `resilience-alpha/*:dev` n'existent sur aucun registre : elles se construisent en local. `up` sans `--build` tente de les télécharger. | Ajouter `--build` : `docker compose --env-file .env -f infra/compose/docker-compose.yml up -d --build --wait`. Construire d'abord `anomaly-detector` (voir le README). |
| `failed to copy: httpReadSeeker ... cloudfront.docker.com ... EOF` | Connexion coupée pendant le téléchargement d'une image publique (postgres, modsecurity-crs, docker-socket-proxy). Problème réseau, pas de dépôt. | Relancer la même commande : les couches déjà reçues sont conservées. Sinon tester `docker pull postgres:16-alpine` seul, changer de réseau (partage 4G), vérifier DNS/MTU. |
