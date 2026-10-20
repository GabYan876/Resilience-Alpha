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

# 2. entraînement (écrit ml/models/isolation_forest.joblib)
docker compose --env-file .env -f infra/compose/docker-compose.yml run --rm \
  -v ./ml/data:/data:ro -v ./ml/models:/models -e DATASET_PATH=/data/normal.csv \
  anomaly-detector python -m app.cli train
```

Sans modèle, le service refuse de démarrer (erreur claire dans les logs) : mieux qu'un détecteur muet.

## Limites connues

- Une cible **arrêtée** n'est pas le cas d'usage du ML (panne binaire) : elle relève du health check
  périodique (scénario S3).
- `attacker_ip` n'est pas renseigné : l'IP viendra des logs du WAF (Loki) quand `BlockIpAction`
  existera. Tant que la politique n'a que `RestartServiceAction`, ce n'est pas bloquant.
- Seul `IncidentKind.AVAILABILITY` est émis. La compromission (SQLi/exfiltration) demandera un
  second détecteur (logs WAF) : on ajoute une classe, on ne modifie pas `DetectionService`.
- Le fichier `.joblib` est du code désérialisé : monté en lecture seule, jamais issu d'une source
  non fiable.

## Tests

```bash
cd services/anomaly-detector && python -m pytest
```

Sur un PC où une stratégie de contrôle d'application bloque les DLL de numpy/scipy, lancer les
tests dans un conteneur (`docker run --rm -v .:/w -w /w python:3.12-slim sh -c "pip install -r requirements.txt pytest && pytest"`).
