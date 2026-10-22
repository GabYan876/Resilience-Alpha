# PROJECT RESILIENCE-ALPHA

> Cyber-résilience et reprise autonome — Workshop national EPSI Bac+5, session octobre 2026.

Plateforme de paiement **fictive** et conteneurisée, capable d'encaisser une attaque lancée depuis un second PC, de la **détecter par machine learning** et de **se réparer seule** (Zero-Touch Recovery). La reprise est prouvée par une nouvelle transaction réussie.

> ⚠️ Environnement de laboratoire. Toutes les données sont fictives. Les attaques sont strictement limitées au PC Hôte du consortium : aucun réseau campus, autre groupe ou service Internet.

## Scénario de démonstration

1. **Avant** : le dashboard montre les services sains ; une transaction de test réussit.
2. **Attaque** : flood HTTP contrôlé depuis le PC Attaquant vers l'API (bonus : injection SQL bloquée par le WAF).
3. **Détection** : métriques (Prometheus) et logs (Loki) montrent un pic anormal ; le modèle ML signale l'anomalie.
4. **Remédiation automatique** : décision → blocage de la source (IP et compte, via le WAF) → redémarrage/mise à l'échelle de l'API.
5. **Vérification** : l'API répond **et** une nouvelle transaction passe → incident clos.

## Architecture

```
 PC Attaquant ──► WAF ──► Gateway (Caddy + front React) ──► API métier ──► BDD
                  │                          │  └─► Auth
                  ▼                          ▼
              Logs / métriques ──► Prometheus · Loki ──► Grafana / SIEM
                                        │
                                        ▼
                              Détecteur ML (anomalies)
                                        │
                                        ▼
        Moteur de remédiation : Décision ─► Actions ─► Vérification
                                        │  (via docker-socket-proxy)
                                        ▼
                               Dashboard Grafana (supervision)

 Assistant RAG (Ollama + LangChain) — isolé, lecture seule, sans droits privilégiés
```

Chaque service Python suit une architecture en couches respectant **SOLID** (`domain` / `application` / `adapters` / `api`, injection de dépendances dans `main.py`). Détails et règles : voir [`CLAUDE.md`](CLAUDE.md).

## Les 5 piliers

| Pilier | Contenu |
|---|---|
| Développement | Microservices FastAPI (BDD, API, auth), front de paiement React/Tailwind, moteur de remédiation, dashboard de supervision Grafana |
| Infrastructure | Docker Compose, Ansible, Prometheus, Grafana, Loki |
| IA / Data | Détection d'anomalies (ML), assistant RAG Ollama + LangChain (≤ 8B) |
| Cybersécurité | Attaques Red Team, WAF, SIEM/SOC, durcissement, Vault/SOPS |
| Gouvernance | EBIOS RM, PCA/PRA, NIS2/DORA |

## Structure du dépôt (cible)

```
.
├── services/
│   ├── api/              # API métier (transactions)
│   ├── auth/             # service d'authentification
│   ├── remediation/      # moteur de remédiation (détection → décision → action → vérification)
│   ├── anomaly-detector/ # ML d'anomalies
│   ├── rag-assistant/    # assistant Ollama + LangChain
│   └── db/               # schéma et migrations
├── frontend/             # front de paiement (React/Tailwind) ; le dashboard est dans infra/observability (Grafana)
├── infra/
│   ├── compose/          # docker-compose*.yml
│   ├── ansible/          # Deploy.ps1 + playbooks/rôles Ansible (voir infra/ansible/README.md)
│   ├── observability/    # Prometheus, Grafana, Loki
│   ├── waf/              # ModSecurity + OWASP CRS, liste de blocage (njs)
│   └── secrets/          # SOPS (chiffré uniquement)
├── attack/               # scripts Red Team (PC Attaquant)
├── ml/                   # jeux de données, notebooks, entraînement
├── scripts/              # vérif. de transaction, reset de démo, chaos
├── docs/                 # architecture, EBIOS RM, PCA/PRA, NIS2/DORA, procédures (indexées par le RAG)
├── CLAUDE.md
└── README.md
```

## Prérequis

**PC Hôte** : Windows 10/11 (droits admin), virtualisation activée, Docker Desktop + WSL2, 4 cœurs min., 16 Go RAM (32 Go recommandés), 50 Go libres SSD.
**PC Attaquant** : poste distinct, 8 Go RAM min., outils des scénarios retenus.
**PC IA (optionnel)** : héberge uniquement Ollama si le PC Hôte manque de RAM.

**Réseau** : réseau privé du binôme — point d'accès mobile Windows `RESILIENCE-G<n>` (PC Hôte en `192.168.137.1`) ou box personnelle, peu importe lequel (voir arbitrage du 21/10, `docs/gouvernance/06-pilotage-arbitrages.md`) ; jamais le campus, un autre groupe ni Internet. Seul le point d'entrée (WAF/front) est publié ; BDD, secrets et interfaces de gestion restent sur des réseaux internes.

## Démarrage rapide

> Ce qui tourne aujourd'hui : PostgreSQL, l'API métier, le service `auth`, la passerelle Caddy (front Pay-Now), le moteur de remédiation (Compose) et la pile d'observabilité, le détecteur ML (Compose ; il exige un modèle entraîné, voir `services/anomaly-detector/README.md`), le WAF ModSecurity + OWASP CRS (seul point d'entrée, `infra/compose/docker-compose.yml`) et l'assistant RAG (`services/rag-assistant/`, Compose ; il exige un Ollama joignable, voir son README).

> **Écarts restants** (échéance jeudi, voir `docs/validation-jalon-21-10.md` §8) : Exposition de la pile testée en réel le 21/10 sur la box (`WAF_BIND_HOST`) ; pile accessible sur n'importe quel réseau privé du binôme. Secrets chiffrés via SOPS + age, rotation branchée et essayée en réel le 21/10, voir `docs/gouvernance/06-pilotage-arbitrages.md`. Restauration de la BDD (`RestoreDatabaseAction`, scénario S4) implémentée et essayée le 20/10, voir `docs/gouvernance/02-pca-pra.md`.

Matériel : voir **Prérequis** ci-dessus. En plus : Docker ≥ 28 et Compose ≥ v2.30, Git Bash pour les scripts `.sh`, Python 3 pour `scripts/` et `attack/`. Toutes les commandes se lancent **depuis la racine du dépôt**, dans Git Bash.

```bash
# 1. Configuration (aucun secret n'est versionné)
cp .env.example .env
#    Remplacer chaque « remplacer-par-un-... » : mots de passe, PROBE_TOKEN, REMEDIATION_INGEST_TOKEN,
#    GRAFANA_ADMIN_PASSWORD, et JWT_SECRET (≥ 32 caractères) :
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Modèle ML : absent d'un clone neuf (ml/models/* est ignoré par Git, un .joblib est du code
#    désérialisé) et le détecteur refuse de démarrer sans lui. On le construit et on l'entraîne
#    sur le jeu versionné ml/data/normal.csv. On passe par `docker run` et non `compose run` :
#    le service monte /models en lecture seule, ce qui empêche d'y écrire le modèle.
#    MSYS_NO_PATHCONV=1 évite que Git Bash réécrive les chemins.
docker compose --env-file .env -f infra/compose/docker-compose.yml build anomaly-detector
MSYS_NO_PATHCONV=1 docker run --rm --env-file .env -v "$(pwd -W)/ml/data:/data:ro" -v "$(pwd -W)/ml/models:/models"   -e DATASET_PATH=/data/normal.csv -e MODEL_PATH=/models/isolation_forest.joblib   resilience-alpha/anomaly-detector:dev python -m app.cli train

# 3. Socle : base, migrations (avec le jeu de données fictif), API, auth, passerelle, WAF,
#    moteur de remédiation, détecteur. --env-file est obligatoire : sans lui PostgreSQL refuse de démarrer.
docker compose --env-file .env -f infra/compose/docker-compose.yml up -d --build --wait

# 4. Observabilité (pile autonome, lancée après le socle qui crée `resilience-net`)
docker compose --env-file .env -f infra/compose/docker-compose.observability.yml up -d --wait

# 5. Vérifier le socle
./scripts/check_transaction.sh  # API saine + transaction de test réglée
```

Dépannage : les lignes `pull access denied for resilience-alpha/...` sont sans gravité (ces images sont construites en local, Compose tente d'abord un téléchargement). `container resilience-anomaly-detector is unhealthy` signifie presque toujours que le modèle de l'étape 2 manque (`ls ml/models/isolation_forest.joblib`). `docker compose ... config --quiet` valide le fichier et signale une variable manquante ; `docker compose ... logs <service>` donne la cause d'un service qui ne devient pas sain ; `./scripts/reset_demo.sh` remet la base à zéro. Détails du modèle : `services/anomaly-detector/README.md`.

Déploiement en une commande (Windows + Docker Desktop, `.env` déjà présent) : `.\infra\ansible\Deploy.ps1` enchaîne contrôle du `.env`, modèle ML si absent, socle, observabilité, vérification Ansible et transaction de test. Détails et limites : `infra/ansible/README.md`.

Accès actuel : front Pay-Now sur `http://${WAF_BIND_HOST:-127.0.0.1}:8080` (via le WAF, puis la passerelle qui ne route que `/auth/*` et `/me/*` ; `/metrics`, `/health` et la sonde `POST /transactions` restent internes), Grafana et son dashboard sur `http://${WAF_BIND_HOST:-127.0.0.1}:8080/grafana/` (même WAF, route `/grafana` de la passerelle ; plus aucun port 3000 publié). `WAF_BIND_HOST` (`.env`) vaut `127.0.0.1` par défaut ; le fixer à l'IP LAN du PC Hôte sur le réseau privé du binôme (jamais `0.0.0.0`) pour un essai réel depuis le PC Attaquant — hotspot (`192.168.137.1`) ou box (ex. `192.168.1.140`), peu importe lequel. Le `.env` doit définir `JWT_SECRET` (≥ 32 caractères, voir `.env.example`). Exemple sur le hotspot : front `http://192.168.137.1:8080/`, dashboard `http://192.168.137.1:8080/grafana/` (renseigner `GRAFANA_ROOT_URL` à la même URL dans `.env`) ; même principe sur une box, avec son IP à la place.

## Lancer la démonstration

```bash
# Sur le PC Attaquant : flood authentifié (voir attack/flood_http.py pour les garde-fous)
# Remplacer l'IP par celle du PC Hôte sur le réseau privé du binôme (hotspot ou box).
python attack/flood_http.py --base-url http://192.168.137.1:8080 --duration 30

# Sur le PC Hôte : observer le dashboard / Grafana, puis vérifier la reprise
./scripts/check_transaction.sh
./scripts/reset_demo.sh         # remise à zéro pour rejouer (purge aussi les sauvegardes S4)

# Preuve de rejouabilité : N cycles reset -> flood -> reprise -> transaction, RTO mesuré
python scripts/demo_loop.py --runs 5
```

Scénario S4 (corruption de la base, restauration automatique) : [`docs/procedures/s4-corruption-bdd.md`](docs/procedures/s4-corruption-bdd.md) ; service : [`services/db/recovery/README.md`](services/db/recovery/README.md).

Critère de réussite : **aucune intervention humaine** entre l'attaque et la nouvelle transaction réussie.

## Tests

```bash
# Un service à la fois : les paquets `app` de chaque service entrent en collision
cd services/api         && python -m pytest -q   # unitaires (domaine sans I/O, adaptateurs avec doubles)
cd services/remediation && python -m pytest -q
cd services/rag-assistant && python -m pytest -q
./scripts/chaos.sh          # injection de défaillances (jeudi, à écrire)
```

## Sécurité

- Moteur de remédiation : accès Docker via **docker-socket-proxy** / API restreinte à token, jamais le socket brut.
- Assistant RAG : lecture seule, aucun accès privilégié.
- Secrets : Vault ou SOPS, jamais en clair dans le dépôt ni dans l'archive de rendu.
- Bloquer une attaque ≠ corriger une compromission : les réponses à un flood (disponibilité) et à une exfiltration/injection (intégrité/confidentialité) sont distinctes.

## Équipe

| Membre | Rôle |
|---|---|
| Hugo | Infra + Cyber |
| Kevin | Tech lead + remédiation / ML |
| Antoine | Dev backend, EBIOS RM, PCA/PRA |
| Gabriel | Dev front, NIS2/DORA, pitch, vérification du dashboard Grafana |
| François | IA RAG, Red Team, assemblage du Dossier |

## Planning

| Jour | Objectif |
|---|---|
| Lun 19/10 | Architecture, EBIOS, dépôt, hotspot |
| Mar | Socle Compose + Ansible, microservices, observabilité, fil rouge bout en bout |
| Mer | Intégration WAF/SIEM/ML/remédiation/dashboard, RAG, tests de restauration |
| Jeu | Chaos, ≥ 5 démos sans intervention, clip, gel du code 17h, remise avant 23h59 |
| Ven | Jury local (5 min démo + 5 min questions) |

## Rendus

`Workshop2026-M2-G<n>/` : `-Dossier.pdf`, `-Pres.pptx`, `-VidChrono.mp4` (≤ 60 s, sans coupe), `-Code.zip`.

## Limites connues

À compléter au fil du sprint (limites du modèle ML, périmètre NIS2/DORA démontrable par un prototype, écarts avec un contexte industriel).

- **Consigne additionnelle 1 (22/10)** : authentification du back-office par caméra USB, reconnaissance de visage, habilitations et ESP8266 (LED bicolore). Conception dans [`docs/consigne-additionnelle-1.md`](docs/consigne-additionnelle-1.md) ; **non implémentée à ce jour**. Même livrée, la détection de vivacité (photo devant la caméra) ne serait pas couverte.
- **Compromission (S2) non automatique** : aucun détecteur n'émet `IncidentKind.COMPROMISE`. La réponse à une injection SQL (rotation de secret via `SopsSecretRotator` + redémarrage de `auth`/`api`) existe et est prouvée, mais l'incident est **déclenché à la main** par `POST /incidents kind=compromise` ; seules les attaques de disponibilité (S1, flood) et de données (S4, corruption BDD) sont traitées sans intervention humaine. L'investigation manuelle de compromission n'est pas développée. Voir `docs/procedures/chaos-engineering.md` (S2) et `docs/gouvernance/02-pca-pra.md` §2.
- **Assistant RAG — injection de prompt (ER6)** : la défense par le prompt n'est pas étanche, même sur `llama3.1:8b` (banc `attack/rag_prompt_injection/` : 9/10 repoussées, cède sur une injection conditionnelle ciblée). Risque résiduel borné par l'absence d'outils, de secrets et d'écriture, et par un corpus non confidentiel.
