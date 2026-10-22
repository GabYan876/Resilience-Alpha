# PROJECT RESILIENCE-ALPHA — Dossier technique

**Workshop Bac+5 M2 — Groupe 8**
Plateforme de paiement fictive conteneurisée, auto-réparante (Zero-Touch Recovery).

> Source de ce document : dépôt `Resilience-Alpha`. Les chiffres proviennent d'essais réels
> consignés dans [`gouvernance/02-pca-pra.md`](gouvernance/02-pca-pra.md) §7 et
> [`repartition-reelle.md`](repartition-reelle.md). Règles du projet : [`CLAUDE.md`](../CLAUDE.md).
> Document source (Markdown) ; export PDF pour la remise `Workshop2026-M2-G8-Dossier.pdf`.

---

## 1. Résumé exécutif

Resilience-Alpha est une plateforme de paiement **fictive**, entièrement conteneurisée, qui
subit une attaque lancée depuis un second poste (PC Attaquant), la **détecte par apprentissage
automatique**, se **répare sans intervention humaine**, et **prouve la reprise par une nouvelle
transaction de test réussie**. Le service est observable **avant, pendant et après** l'incident
dans un tableau de bord Grafana.

Principe directeur : *un conteneur qui redémarre ne prouve rien*. Un incident n'est déclaré clos
que lorsque l'API répond **et** qu'une transaction de sonde passe.

Résultat mesuré (chaos du 22/10, 5 passages consécutifs sans intervention) : **5/5 reprises
automatiques**, RTO moyen 32 s (max 36 s), transaction de test réussie à chaque passage.

---

## 2. Mission et fil rouge

| Temps | Ce que montre la démonstration |
|---|---|
| Avant | Service sain, trafic de fond légitime, transactions qui passent |
| Pendant | Attaque réelle depuis le PC Attaquant à travers le WAF ; détection ML ; décision ; action |
| Après | Reprise automatique, vérifiée par une transaction de sonde ; état observable dans Grafana |

La démonstration est **rejouable en boucle** (≥ 5 passages) grâce à un script de remise à l'état
initial (`scripts/reset_demo.sh`) et au pilote `scripts/demo_loop.py`.

Configuration de la démonstration (vendredi) : réseau privé du binôme, **hotspot Windows,
PC Hôte en `192.168.137.1`**, seul le WAF publié (`192.168.137.1:8080`). Ollama hébergé sur un
PC Linux dédié (`192.168.137.157:11434`). Jamais le réseau du campus, un autre groupe ni Internet.

---

## 3. Architecture

### 3.1 Vue d'ensemble

Le PC Hôte héberge toute la plateforme en Docker Compose, répartie sur des réseaux cloisonnés ;
seul le WAF publie un port. Le PC Attaquant n'atteint la plateforme que par le WAF. Détail et
schéma : [`architecture/architecture.md`](architecture/architecture.md).

- **Réseau public** : WAF (ModSecurity + OWASP CRS) → passerelle Caddy (front React servi en
  statique, routage `/auth/*`, `/me/*`, `/grafana`).
- **Réseau app (interne)** : API métier, auth, PostgreSQL, `db-recovery`.
- **Réseau obs (interne)** : Prometheus, Loki + Alloy, Grafana.
- **Réseau control (interne)** : détecteur ML, moteur de remédiation, `docker-proxy-ctl`, secrets
  SOPS (fichiers chiffrés montés).
- **Réseau rag (isolé)** : assistant RAG, seul membre ; aucun chemin vers l'API, la base, le
  moteur ni Docker.

### 3.2 Principes SOLID (architecture hexagonale)

Chaque service Python suit une architecture en couches `domain` / `application` / `adapters` /
`api` ; les dépendances pointent vers le domaine. Le moteur de remédiation en est l'exemple le
plus net : détection, décision, action et vérification sont des composants séparés (S), un
nouveau type d'attaque ou d'action s'ajoute par une classe enregistrée dans un registre sans
modifier l'existant (O), toute implémentation d'un port est interchangeable avec un *fake* en
test (L), les ports sont petits et ciblés — `ContainerRestarter`, `IpBlocker`, `HealthChecker`,
`TransactionProbe`… (I), et les adaptateurs concrets (Docker, HTTP, SOPS) sont injectés dans le
composition root (D).

---

## 4. Les cinq piliers

### 4.1 Dev

- Microservices **Python / FastAPI** : API métier, auth, BDD, `db-recovery`.
- Front de paiement **React + Tailwind CSS** (servi en statique derrière le WAF).
- **Moteur de remédiation** (pipeline `Detector → DecisionPolicy → RemediationAction[] →
  RecoveryVerifier`).
- Tableau de bord de supervision **Grafana** provisionné
  (`infra/observability/grafana/dashboards/resilience-alpha.json`), alimenté par Prometheus et
  Loki (décision du 20/10 : pas de dashboard React).

### 4.2 Infra

- Orchestration **Docker Compose** (deux piles autonomes : socle et observabilité), automatisation
  **Ansible** ; déploiement reproductible en une commande.
- Observabilité **Prometheus + Grafana + Loki** (ingestion par **Alloy**, pas Promtail ni Elastic).
- Contrainte RAM (PC Hôte 16 Go) : `mem_limit` sur chaque conteneur ; référence mesurée au repos
  885 Mo, pic 990 Mo sous flood ; Ollama déporté sur un 3e PC.

### 4.3 IA / Data

- **Détection d'anomalies par ML** : `IsolationForest` (scikit-learn) sur des métriques
  Prometheus (débit de requêtes, taux d'erreur, latence p95, disponibilité) et des logs Loki.
  Pas de règles codées en dur ; seuil appris, confirmation sur 3 mesures avant alerte.
- **Assistant RAG** : Ollama + LangChain, modèle `llama3.1:8b` (≤ 8B paramètres), embeddings
  `nomic-embed-text`. Lecture seule sur la documentation indexée, **aucun outil, aucun accès
  privilégié**. Interrogé hors ligne via `docker compose exec`.

### 4.4 Cyber

- **Attaque réelle** depuis le PC Attaquant : `attack/flood_http.py` (déni de service applicatif)
  et `attack/sqli_injection.py` (injection SQL). Garde-fous `ALLOWED_HOSTS` : toute cible hors
  périmètre exige `--yes-i-know-the-target`, jamais utilisé en démonstration.
- **WAF** ModSecurity + OWASP CRS (niveau de paranoïa 1), seul point d'entrée.
- **SOC** : fonction SIEM assurée par Loki + Grafana (décision du 21/10 : pas de Wazuh).
- **Secrets** : SOPS + age (choix du 21/10), aucun secret en clair dans le dépôt, les images, les
  logs ni le zip ; `.env` ignoré, `.env.example` fourni ; rotation `SopsSecretRotator` essayée en
  réel.
- **Durcissement** : réseaux Docker internes, `docker-socket-proxy` à endpoints restreints
  (jamais `docker.sock` en direct), `cap_drop`, `no-new-privileges`, conteneurs en lecture seule.

### 4.5 Gouvernance

- **EBIOS Risk Manager** : ateliers 1 à 5 ([`gouvernance/01-ebios-rm.md`](gouvernance/01-ebios-rm.md)).
  Événements redoutés ER1 à ER8, scénarios stratégiques SS1 à SS6, scénarios opérationnels reliés
  aux scripts d'attaque réels, traitement du risque avec risque résiduel.
- **PCA / PRA** : [`gouvernance/02-pca-pra.md`](gouvernance/02-pca-pra.md), RTO/RPO cibles et
  mesurés, journal des essais.
- **NIS2 / DORA** : [`gouvernance/03-nis2-dora.md`](gouvernance/03-nis2-dora.md), exigences
  pertinentes reliées au démonstrateur et obligations non démontrables par un prototype de 4 jours.
- **AMDEC** et **matrice de traçabilité** : [`gouvernance/05-amdec.md`](gouvernance/05-amdec.md),
  [`gouvernance/04-matrice-tracabilite.md`](gouvernance/04-matrice-tracabilite.md).

---

## 5. Le moteur de remédiation (cœur de la preuve)

`Detector (ML) → DecisionPolicy → RemediationAction[] → RecoveryVerifier`. Chaque étape émet un
événement JSON (`incident.detected`, `decision.made`, `action.executed`,
`verification.completed`, `incident.resolved`) consommé par Loki, donc par Grafana.

La décision distingue explicitement **restauration de disponibilité** et **correction de
compromission** :

| Type d'incident | Déclencheur | Actions |
|---|---|---|
| `AVAILABILITY` | flood HTTP | `BlockIpAction` → `BlockSubjectAction` → `RestartServiceAction` |
| `CRASH` | conteneur arrêté | `RestartServiceAction` |
| `DATABASE_CORRUPTION` | altération BDD | `RestoreDatabaseAction` → `RestartServiceAction` → vérification |
| `COMPROMISE` | SQLi / exfiltration | `RotateSecretAction` (JWT) → redémarrage `auth` puis `api` |

La clôture d'un incident exige toujours : **API saine ET transaction de sonde réussie**.

---

## 6. Essais réels et chiffres

Mesure du RTO (décision du 19/10) : du **début d'attaque** (journal horodaté du script) à
l'événement `incident.resolved` dans Loki. Journal complet :
[`gouvernance/02-pca-pra.md`](gouvernance/02-pca-pra.md) §7.

| Scénario | Résultat | RTO / RPO | Intervention |
|---|---|---|---|
| S1 flood, `demo_loop.py --runs 5` (22/10) | 5/5 reprises, transaction de test OK à chaque passage | RTO moyen 32 s, max 36 s | **Non** |
| S1 flood depuis PC Attaquant via WAF (22/10) | reprise auto (`block_subject` + `restart_service`) | RTO 4,84 s (remédiation) | **Non** |
| S4 corruption BDD, pile complète (21/10, 2 passages) | restauration auto, transaction OK | RTO 3,24–3,79 s ; RPO 13,56–59,32 s | **Non** |
| S2 SQLi depuis PC Attaquant via WAF (22/10) | 6/6 charges bloquées (403, règle CRS 942100) | — | **Non** |
| S2 compromission (déclenchement manuel `POST /incidents kind=compromise`) | rotation JWT, redémarrage `auth`/`api`, `incident.resolved` | — | déclenchement manuel |
| Faux positifs ML (21/10) | 0/120 mesures anormales, attaque toujours détectée | — | — |
| ER6 injection de prompt, banc 6 scénarios / 10 questions (22/10) | `llama3.1:8b` 9/10 repoussées ; `llama3.2:3b` 5/10 | — | — |

---

## 7. Limites connues et risques résiduels

Présentées honnêtement, comme limites assumées (voir « Limites connues » du
[`README.md`](../README.md)) :

- **Compromission (S2) non automatique** : aucun détecteur n'émet `IncidentKind.COMPROMISE`. La
  réponse (rotation de secret + redémarrage) est prouvée mais l'incident est déclenché à la main ;
  seules la disponibilité (S1) et les données (S4) sont traitées sans intervention humaine.
  L'investigation manuelle de compromission n'est pas développée.
- **`block_ip` inopérant sous Docker Desktop** : l'IP de l'attaquant est NATée derrière la
  passerelle Docker ; le blocage se fait par **compte** (`sub` du JWT). Un attaquant peut créer
  d'autres comptes ; l'IP resterait exploitable sur un hôte Linux.
- **Assistant RAG (ER6)** : la défense par le prompt n'est pas étanche, même sur `llama3.1:8b`
  (cède sur une injection conditionnelle ciblée). Risque résiduel borné par l'absence d'outils, de
  secrets et d'écriture, et par un corpus non confidentiel.
- **Sauvegardes S4** : locales, non chiffrées, non répliquées ; pire cas théorique ≈ 315 s,
  au-dessus de la cible de 5 min. Protègent de la corruption logique, pas de la perte de l'hôte.
- **Modèle ML** : le score d'IsolationForest sature ; seuil à recalibrer sur trafic réel.
- **Consigne additionnelle 1** (authentification du back-office par caméra, reconnaissance de
  visage, ESP8266) : conçue ([`consigne-additionnelle-1.md`](consigne-additionnelle-1.md)), **non
  implémentée**. La détection de vivacité ne serait de toute façon pas couverte.

---

## 8. Reproductibilité

- Déploiement en une commande (Docker Compose + Ansible) ; voir [`README.md`](../README.md) et
  [`dev.md`](dev.md).
- Secrets rendus localement via `scripts/render_env.sh` ; aucun secret dans le `-Code.zip`.
- Démonstration rejouable : `scripts/reset_demo.sh` puis `python scripts/demo_loop.py --runs 5`.
- Tout le code (y compris généré) est compris et explicable par son auteur devant le jury.

---

## 9. Rendus

`Workshop2026-M2-G8/` : `-Dossier.pdf` (ce document), `-Pres.pptx`, `-VidChrono.mp4` (≤ 60 s, sans
coupe), `-Code.zip` (sources, infra, scripts d'attaque/ML, tests, doc API, README, **sans secret**).
