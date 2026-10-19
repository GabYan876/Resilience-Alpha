# Pile d'observabilité — Prometheus, Loki, Alloy, Grafana

Rend l'incident visible **avant / pendant / après**, et montre le pipeline de
remédiation. Provisionnée sans aucun clic : datasources et dashboard sont du code.

Détail des choix, du dashboard et du risque lié au socket Docker :
[`docs/architecture/observabilite.md`](../../docs/architecture/observabilite.md).

## Services

| Service | Image | RAM | Rôle |
|---|---|---|---|
| `prometheus` | `prom/prometheus:v3.1.0` | 512 Mo | métriques, scrape `api`, `auth`, `remediation`, `anomaly-detector` sur `:8000/metrics` |
| `loki` | `grafana/loki:3.4.2` | 384 Mo | logs, mode `single-binary`, stockage fichier, rétention 24 h |
| `alloy` | `grafana/alloy:v1.7.1` | 128 Mo | collecte les logs des conteneurs et les pousse vers Loki |
| `grafana` | `grafana/grafana:11.5.2` | 256 Mo | **seule interface consultable** |
| `docker-proxy` | `ghcr.io/tecnativa/docker-socket-proxy:v0.5.0` | 32 Mo | passerelle Docker en lecture seule : seul conteneur à voir le socket |

Total **1 312 Mo**. Aucun service superflu : pas d'Alertmanager (les seuils codés
en dur sont exclus par le sujet, la détection appartient au ML), pas de
node-exporter, pas de cAdvisor.

Alloy ne touche **jamais** le `docker.sock` : il interroge `docker-proxy`, limité à
`CONTAINERS=1` et `NETWORKS=1` en lecture seule, sur un réseau `internal: true`
que personne d'autre ne joint. Conforme à la règle non négociable de `CLAUDE.md`.

## Exposition réseau

`obs-internal` est en `internal: true`, sans route sortante. Prometheus, Loki et
Alloy ne publient **aucun** port. Prometheus est aussi sur `resilience-net` pour
scraper les services métier par DNS. Grafana est liée à `127.0.0.1:3000` et
joignable via le WAF.

`resilience-net` est déclaré `external: true` : il appartient à la pile
principale (`infra/compose/docker-compose.yml`), qui le crée.

## Commandes

```bash
# Démarrage (la pile principale doit tourner : elle crée resilience-net)
docker compose --env-file .env -f infra/compose/docker-compose.observability.yml up -d --wait

# Arrêt en conservant les données
docker compose -p resilience-alpha-obs down

# Arrêt + suppression des volumes (repart d'un état vierge)
docker compose -p resilience-alpha-obs down -v
```

Vérifier que la chaîne fonctionne :

```bash
# Cibles : api=1 attendu, les services non encore écrits donnent 0 (signal voulu)
docker exec resilience-prometheus wget -qO- 'http://127.0.0.1:9090/api/v1/query?query=up'

# Les trois labels exigés doivent apparaître : service, trace_id, event
docker exec resilience-loki wget -qO- 'http://127.0.0.1:3100/loki/api/v1/labels'

# Le dashboard doit être provisionné sans intervention
curl -u "admin:$GRAFANA_ADMIN_PASSWORD" 'http://127.0.0.1:3000/api/search?type=dash-db'
```

## Variables obligatoires

Sans elles, la pile refuse de démarrer — un échec explicite vaut mieux qu'un
`admin/admin` silencieux ou un collecteur de logs aveugle.

| Variable | Obtenir la valeur |
|---|---|
| `GRAFANA_ADMIN_PASSWORD` | via SOPS, voir [`docs/dev.md`](../../docs/dev.md) |

Les autres variables ont une valeur par défaut utilisable : voir le tableau
complet dans `docs/architecture/observabilite.md`.

Grafana est publiée sur `127.0.0.1:${GRAFANA_HTTP_PORT:-3000}`. Le port 3000 est
aussi celui du backend Pay-Now : en cas de conflit, changer `GRAFANA_HTTP_PORT`.

## Deux pièges réglés, à ne pas réintroduire

Ils ne se manifestent qu'au démarrage effectif, jamais à la validation de syntaxe.

- **Alloy ne doit pas tourner en `root`.** L'image le fait par défaut, mais Docker
  reporte sur le volume nommé l'ownership `473:473` mode `0770` du répertoire de
  l'image, et `cap_drop: ALL` retire `CAP_DAC_OVERRIDE` — la capacité qui permet à
  root d'ignorer les permissions d'un répertoire qu'il ne possède pas. Résultat :
  `mkdir /var/lib/alloy/data: permission denied` et redémarrage en boucle. D'où
  `user: "473:473"` et le groupe `docker` de l'hôte en groupe supplémentaire, pour
  la seule lecture du socket.
- **`trace_id` ne doit jamais redevenir un label indexé.** L'API métier en génère
  un par transaction, pas par incident. Chaque valeur distincte d'un label crée un
  flux Loki : sous le flood, indexer `trace_id` produirait des milliers de flux,
  Loki rejetterait en `429` et l'on perdrait les événements `incident.*` au moment
  où ils servent de preuve. Il vit en `stage.structured_metadata`, requêtable par
  `| trace_id="..."`. Mesuré : 7 transactions à `trace_id` distincts, 12 flux au
  total, inchangé.
- **`NETWORKS=1` est nécessaire sur le proxy Docker.** `discovery.docker` calcule
  les labels réseau des conteneurs. Avec `CONTAINERS=1` seul, Alloy boucle sur
  `error while computing network labels: 403 Forbidden` et ne collecte rien, tout
  en restant `healthy` — son port répond, il n'a simplement aucune cible.
- **Le dossier de provisionnement et le dashboard ne doivent pas partager un uid.**
  Avec `folderUid` et l'uid du dashboard tous deux à `resilience-alpha`, le
  provisionnement échoue sur `Dashboard cannot be changed to a folder` et la vue
  n'apparaît jamais. Le dossier porte donc `resilience-alpha-folder`.

## Ne pas fusionner avec la pile principale

Ce fichier Compose porte son propre nom de projet, `resilience-alpha-obs`. La pile
est donc autonome et survit aux redémarrages de conteneurs déclenchés par le
moteur de remédiation — indispensable pour montrer l'incident **pendant** qu'il a
lieu. La combiner à la pile principale via plusieurs `-f` écraserait le nom de
projet de celle-ci.
