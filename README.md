# PROJECT RESILIENCE-ALPHA

> Cyber-résilience et reprise autonome — Workshop national EPSI Bac+5, session octobre 2026.

Plateforme de paiement **fictive** et conteneurisée, capable d'encaisser une attaque lancée depuis un second PC, de la **détecter par machine learning** et de **se réparer seule** (Zero-Touch Recovery). La reprise est prouvée par une nouvelle transaction réussie.

> ⚠️ Environnement de laboratoire. Toutes les données sont fictives. Les attaques sont strictement limitées au PC Hôte du consortium : aucun réseau campus, autre groupe ou service Internet.

## Scénario de démonstration

1. **Avant** : le dashboard montre les services sains ; une transaction de test réussit.
2. **Attaque** : flood HTTP contrôlé depuis le PC Attaquant vers l'API (bonus : injection SQL bloquée par le WAF).
3. **Détection** : métriques (Prometheus) et logs (Loki) montrent un pic anormal ; le modèle ML signale l'anomalie.
4. **Remédiation automatique** : décision → blocage de l'IP (WAF/pare-feu) → redémarrage/mise à l'échelle de l'API.
5. **Vérification** : l'API répond **et** une nouvelle transaction passe → incident clos.

## Architecture

```
 PC Attaquant ──► WAF ──► Front (React) ──► API métier ──► BDD
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
                               Dashboard de supervision

 Assistant RAG (Ollama + LangChain) — isolé, lecture seule, sans droits privilégiés
```

Chaque service Python suit une architecture en couches respectant **SOLID** (`domain` / `application` / `adapters` / `api`, injection de dépendances dans `main.py`). Détails et règles : voir [`CLAUDE.md`](CLAUDE.md).

## Les 5 piliers

| Pilier | Contenu |
|---|---|
| Développement | Microservices FastAPI (BDD, API, auth), front React/Tailwind, moteur de remédiation, dashboard |
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
├── frontend/             # front paiement + dashboard (React/Tailwind)
├── infra/
│   ├── compose/          # docker-compose*.yml
│   ├── ansible/          # playbooks
│   ├── observability/    # Prometheus, Grafana, Loki
│   ├── waf/              # règles ModSecurity/Coraza
│   └── secrets/          # Vault / SOPS (chiffré uniquement)
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

**Réseau** : point d'accès mobile Windows `RESILIENCE-G<n>`, PC Hôte en `192.168.137.1`. Seul le point d'entrée (WAF/front) est publié ; BDD, secrets et interfaces de gestion restent sur des réseaux internes.

## Démarrage rapide

> Ce qui tourne aujourd'hui : PostgreSQL, l'API métier, le service `auth`, la passerelle Caddy (front Pay-Now), le moteur de remédiation (Compose) et la pile d'observabilité, et le détecteur ML (Compose ; il exige un modèle entraîné, voir `services/anomaly-detector/README.md`). le WAF ModSecurity + OWASP CRS (seul point d'entrée, `infra/compose/docker-compose.yml`). L'assistant RAG et les playbooks Ansible (`infra/ansible/`) restent à venir.

```bash
# 1. Configuration (aucun secret n'est versionné)
cp .env.example .env            # puis renseigner les secrets (Vault/SOPS)

# 2. Socle : base, migrations, API, moteur de remédiation
#    --env-file est obligatoire : sans lui PostgreSQL refuse de démarrer.
docker compose --env-file .env -f infra/compose/docker-compose.yml up -d --build --wait

# 3. Observabilité (pile autonome, lancée après le socle qui crée `resilience-net`)
docker compose --env-file .env -f infra/compose/docker-compose.observability.yml up -d --wait

# 4. Vérifier le socle
./scripts/check_transaction.sh  # API saine + transaction de test réglée
```

La cible reste un déploiement en une commande via Ansible (`infra/ansible/site.yml`, à écrire).

Accès actuel (poste hôte uniquement) : front Pay-Now sur `http://127.0.0.1:8080` (via le WAF, puis la passerelle qui ne route que `/auth/*` et `/me/*` ; `/metrics`, `/health` et la sonde `POST /transactions` restent internes), Grafana sur `http://127.0.0.1:3000`. Le `.env` doit définir `JWT_SECRET` (≥ 32 caractères, voir `.env.example`). Cible : front, Grafana et dashboard via le WAF sur `192.168.137.1`.

## Lancer la démonstration

```bash
# Sur le PC Attaquant : flood authentifié (voir attack/flood_http.py pour les garde-fous)
python attack/flood_http.py --base-url http://192.168.137.1:8080 --duration 30

# Sur le PC Hôte : observer le dashboard / Grafana, puis vérifier la reprise
./scripts/check_transaction.sh
./scripts/reset_demo.sh         # remise à zéro pour rejouer

# Preuve de rejouabilité : N cycles reset -> flood -> reprise -> transaction, RTO mesuré
python scripts/demo_loop.py --runs 5
```

Critère de réussite : **aucune intervention humaine** entre l'attaque et la nouvelle transaction réussie.

## Tests

```bash
# Un service à la fois : les paquets `app` de chaque service entrent en collision
cd services/api         && python -m pytest -q   # unitaires (domaine sans I/O, adaptateurs avec doubles)
cd services/remediation && python -m pytest -q
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
| Gabriel | Dev front, dashboard, NIS2/DORA, pitch |
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
