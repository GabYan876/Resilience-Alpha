# anomaly-detector

Détecteur d'anomalies ML (pilier IA/Data). Il lit l'état du service dans Prometheus, juge chaque
mesure avec un modèle **IsolationForest** et signale au moteur de remédiation par
`POST /incidents` (jeton Bearer). Il ne décide ni n'agit : détection ≠ décision ≠ action.

## Fonctionnement

```
Prometheus ──> PrometheusMetricsSource ──> DetectionService ──> HttpAnomalyReporter ──> remediation
                (4 mesures / 5 s)           │  modèle ML             POST /incidents
                                            └─ confirmation x3, délai de grâce 90 s
```

Un second cas d'usage, `IntegrityWatchService`, surveille la **base** (scénario S4) : il lit
`GET /integrity` de `db-recovery` (3 compteurs, aucune donnée) toutes les `POLL_INTERVAL_S` et signale
`database_corruption` dès qu'un invariant du grand livre est violé : nombre de transactions ou
d'écritures qui **baisse** (les tables sont en ajout seul, `app_rw` n'a pas de `DELETE`), ou
transaction dont les écritures ne s'équilibrent pas. Après un signalement, la référence est oubliée
et réapprise (la restauration fait reculer les compteurs légitimement), puis `COOLDOWN_S` de silence.

Les 4 mesures (`app/domain/models.py`) : débit de requêtes, part de 5xx, latence p95, `up`.

Pas de règle codée en dur : le seuil d'alerte est **appris** à l'entraînement (plus mauvais score
du trafic normal, moins une marge). Deux garde-fous évitent les faux positifs et les doubles
signalements : `CONFIRMATIONS` jugements anormaux consécutifs, puis `COOLDOWN_S` de silence.

Le score est exposé en métrique (`anomaly_score`, `anomaly_detected` sur `/metrics`) pour le
dashboard.

## Constituer le modèle

Le modèle (`ml/models/`) et les données (`ml/data/*.csv`) sont ignorés par Git : on les reconstruit.
La pile (API, Prometheus) doit tourner, avec du **trafic normal** (pas d'attaque pendant la collecte).

```bash
# 0. dans un autre terminal : trafic de fond normal (alterne calme / normal / chargé).
#    Prérequis : pile démarrée et `scripts/seed_demo.py` lancé. Laisser tourner pendant la collecte.
python scripts/background_traffic.py --duration 900

# 1. ~10 min d'échantillons pendant que le trafic tourne
docker compose --env-file .env -f infra/compose/docker-compose.yml run --rm \
  -v ./ml/data:/data -e DATASET_PATH=/data/normal.csv anomaly-detector \
  python -m app.cli collect --count 120 --interval 5

# 2. entraînement (écrit ml/models/isolation_forest.joblib). `docker run` et non `compose run` :
#    le service monte /models en lecture seule (:ro), qui l'emporte sur un -v en ligne de commande.
MSYS_NO_PATHCONV=1 docker run --rm --env-file .env -v "$(pwd -W)/ml/data:/data:ro"   -v "$(pwd -W)/ml/models:/models" -e DATASET_PATH=/data/normal.csv   -e MODEL_PATH=/models/isolation_forest.joblib   resilience-alpha/anomaly-detector:dev python -m app.cli train
```

Sous Git Bash (Windows), `MSYS_NO_PATHCONV=1` est indispensable : sinon Bash réécrit les chemins
des montages. `$(pwd -W)` donne le chemin Windows de la racine du dépôt (à lancer depuis celle-ci).
Le jeu `ml/data/*.csv` est versionné (données fictives) : un clone neuf peut s'entraîner sans `collect`.

Sous **cmd.exe** ou **PowerShell**, la syntaxe Bash (`MSYS_NO_PATHCONV=1`, `$(pwd -W)`) n'existe pas : Docker
reçoit `$(pwd -W)` tel quel et refuse le montage (« includes invalid characters for a local volume name »).
Lancer plutôt, depuis la racine du dépôt :

```powershell
# PowerShell
docker run --rm --env-file .env -v "${PWD}/ml/data:/data:ro" -v "${PWD}/ml/models:/models" -e DATASET_PATH=/data/normal.csv -e MODEL_PATH=/models/isolation_forest.joblib resilience-alpha/anomaly-detector:dev python -m app.cli train
```

```bat
:: cmd.exe
docker run --rm --env-file .env -v "%cd%/ml/data:/data:ro" -v "%cd%/ml/models:/models" -e DATASET_PATH=/data/normal.csv -e MODEL_PATH=/models/isolation_forest.joblib resilience-alpha/anomaly-detector:dev python -m app.cli train
```

## Mesurer la qualité du modèle

`evaluate` rejoue le modèle sur des mesures **jamais vues à l'entraînement** : il compte les
fausses alertes sur du trafic normal inédit (même règle qu'en ligne : `CONFIRMATIONS` jugements
anormaux de suite) et vérifie que l'attaque est détectée. Le jeu d'attaque s'enregistre comme
le trafic normal (`collect`), flood en cours et détecteur arrêté pour qu'il ne déclenche pas la
remédiation à ce moment-là.

```bash
MSYS_NO_PATHCONV=1 docker compose --env-file .env -f infra/compose/docker-compose.yml run --rm   -v ./ml/data:/data:ro -e DATASET_PATH=/data/normal.csv anomaly-detector   python -m app.cli evaluate --normal /data/holdout.csv --attack /data/attack.csv
```

Sans modèle, le service refuse de démarrer (erreur claire dans les logs) : mieux qu'un détecteur muet.

## Limites connues

- Une cible **arrêtée** n'est pas le cas d'usage du ML (panne binaire) : elle relève du health check
  périodique (scénario S3).
- `attacker_ip` n'est volontairement jamais renseigné : sous Docker Desktop, le WAF voit la
  passerelle Docker (`172.25.0.1`) pour tout le trafic LAN, attaquant ou légitime (mesuré, flood
  réel depuis le PC Attaquant le 21/10), un locator d'IP désignerait la passerelle, pas
  l'attaquant, et `BlockIpAction` couperait tout le monde. `attacker_subject`
  (`LokiAttackerLocator`) est la seule désignation de source fiable dans cet environnement ;
  voir `docs/architecture/architecture.md` et `docs/gouvernance/06-pilotage-arbitrages.md` (20/10).
- `database_corruption` repose sur des **invariants** (compteurs en ajout seul), pas sur le ML : une
  altération qui conserve les compteurs et l'équilibre des écritures (un montant modifié) n'est pas vue.
- Hors corruption de base, seul `IncidentKind.AVAILABILITY` est émis. La compromission (SQLi/exfiltration) demandera un
  second détecteur (logs WAF) : on ajoute une classe, on ne modifie pas `DetectionService`.
- Le fichier `.joblib` est du code désérialisé : monté en lecture seule, jamais issu d'une source
  non fiable.
- Le score brut d'IsolationForest **sature** : au-delà d'un certain débit de requêtes, le score ne
  bouge plus (confirmé par sonde directe du modèle entraîné). Un flood qui n'augmente que le débit
  (sur une route non authentifiée, par ex.) ne franchit donc jamais le seuil : il faut une vraie
  dégradation de `latency_p95_s` et/ou `error_ratio` (voir `attack/flood_http.py`, qui épuise le
  pool de connexions DB de l'API pour provoquer cette dégradation).

## Tests

```bash
cd services/anomaly-detector && python -m pytest
```

Sur un PC où une stratégie de contrôle d'application bloque les DLL de numpy/scipy, ou si
l'environnement local n'a pas joblib/scikit-learn, lancer les tests dans un conteneur jetable
(le conteneur de service tourne en lecture seule, donc pas celui-là) :

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd):/app" -w /app python:3.12-slim \
  sh -c "pip install -q -r requirements.txt pytest && python -m pytest tests/ -q"
```
