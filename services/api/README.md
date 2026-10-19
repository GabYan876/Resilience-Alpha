# API métier — transactions de paiement

Service FastAPI de la plateforme de paiement **fictive** de PROJECT RESILIENCE-ALPHA. Il exécute des virements entre comptes de test, tient un grand livre en double entrée et sert de **preuve de reprise** : le moteur de remédiation ne déclare un incident clos que si `GET /health` répond ET qu'un `POST /transactions` réussit.

Toutes les données sont fictives (IBAN de laboratoire, aucun compte bancaire réel).

- [Vue d'ensemble](#vue-densemble)
- [Référence des routes](#référence-des-routes)
- [Authentification](#authentification)
- [Montants, devises et idempotence](#montants-devises-et-idempotence)
- [Codes de réponse](#codes-de-réponse)
- [Événements et métriques](#événements-et-métriques)
- [Modèle de données](#modèle-de-données)
- [Configuration](#configuration)
- [Lancer, tester, vérifier](#lancer-tester-vérifier)
- [Sécurité et limites connues](#sécurité-et-limites-connues)
- [Contrat avec le moteur de remédiation](#contrat-avec-le-moteur-de-remédiation)

## Vue d'ensemble

| Élément | Valeur |
|---|---|
| Framework | FastAPI, SQLAlchemy 2 asynchrone (asyncpg), Alembic |
| Port interne | `8000` (non publié sur l'hôte : joignable depuis le réseau Docker `resilience-net` sous le nom `api`) |
| Base de données | PostgreSQL 16, réseau interne `db-internal`, rôle `app_rw` (voir [`services/db/README.md`](../db/README.md)) |
| Image | `python:3.12-slim`, utilisateur non-root (uid 10001), `mem_limit: 256m` |
| Documentation interactive | `/docs` (Swagger) et `/openapi.json`, générés par FastAPI |

### Architecture en couches

Les dépendances pointent vers le domaine, jamais l'inverse.

```
app/
  domain/        entités (Account, Transaction, LedgerEntry), erreurs, ports (Protocol)
  application/   cas d'usage : ExecuteTransfer (virement), GetTransaction, GetAccount
  adapters/      persistence/ (SQLAlchemy : modèles, dépôts, unité de travail, sonde de santé)
                 logging_publisher.py (événements JSON sur stdout)
  api/           routes.py (HTTP <-> cas d'usage, sans logique métier), schemas.py (Pydantic)
  config.py      seul endroit qui lit l'environnement
  main.py        composition root : câble les adaptateurs aux ports
```

Les ports (`AccountRepository`, `TransactionRepository`, `UnitOfWork`, `HealthProbe`, `EventPublisher`) sont de petites interfaces `typing.Protocol`. Les tests remplacent les adaptateurs par des doubles en mémoire (`tests/fakes.py`).

## Référence des routes

| Méthode | Chemin | Rôle | Authentification |
|---|---|---|---|
| `GET` | `/health` | Santé de l'API **et** de la base | non |
| `POST` | `/transactions` | Exécuter un virement | jeton (`Bearer`) |
| `GET` | `/transactions/{transaction_id}` | Lire une transaction | non |
| `GET` | `/accounts/{iban_fake}` | Lire un compte et son solde | non |
| `GET` | `/metrics` | Métriques Prometheus (hors schéma OpenAPI) | non |

### `GET /health`

Ne ment pas : exécute un `SELECT 1` sur la base.

`200 OK` :

```json
{ "status": "ok", "database": "up" }
```

`503 Service Unavailable` si la base ne répond pas :

```json
{ "status": "degraded", "database": "down" }
```

### `POST /transactions`

Débite le compte source, crédite le compte destination et écrit les deux lignes du grand livre, **en une seule transaction SQL**.

Corps de la requête :

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `from_account` | chaîne (1–34) | oui | IBAN fictif du compte source |
| `to_account` | chaîne (1–34) | oui | IBAN fictif du compte destinataire |
| `amount_cents` | entier > 0 | un des deux | Montant en centimes (forme canonique) |
| `amount` | décimal > 0 | un des deux | Montant en unités (ex. `1.50`), converti en centimes avec `Decimal` |
| `currency` | chaîne de 3 caractères | non (défaut `EUR`) | Mise en majuscules automatiquement |
| `idempotency_key` | chaîne (≤ 64) | non | Clé d'idempotence ; générée par le serveur si absente |

Il faut fournir **exactement un** de `amount_cents` ou `amount`. Un montant plus précis que le centime (`1.005`) est refusé.

Exemple (depuis un conteneur du réseau `resilience-net`) :

```bash
curl -s -X POST http://api:8000/transactions \
  -H "Authorization: Bearer $PROBE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"from_account":"TEST-0001","to_account":"TEST-0002","amount_cents":100,"idempotency_key":"demo-001"}'
```

Réponse `200 OK` (virement réglé) :

```json
{
  "id": "5d7c0e0a-6a0b-4e1f-9c1b-2f4a9b7e3c11",
  "account_from": "…",
  "account_to": "…",
  "amount_cents": 100,
  "currency": "EUR",
  "status": "settled",
  "idempotency_key": "demo-001",
  "trace_id": "9f2c…",
  "created_at": "2026-10-19T14:02:11.482913Z"
}
```

Valeurs possibles de `status` : `pending`, `settled`, `failed`, `rejected`.

Cas particuliers :

- **Refus métier** (solde insuffisant, devise différente de celle du compte) : réponse **`409`** avec le même corps et `"status": "rejected"`. La transaction refusée est conservée en base comme trace d'audit, les soldes ne bougent pas. Un refus ne doit jamais être lu comme une reprise : c'est pourquoi ce n'est pas un 2xx.
- **Rejeu d'une clé d'idempotence** : la transaction d'origine est renvoyée telle quelle, **sans second débit**. Le code HTTP dépend de son état (200 si réglée, 409 sinon). Le contenu de la requête rejouée n'est pas comparé à l'original.
- **Compte inconnu** : `404`.
- **Même compte source et destination** : `422`.

### `GET /transactions/{transaction_id}`

`transaction_id` est un UUID. Renvoie le même objet que `POST /transactions`.

- `200` : transaction trouvée
- `404` : `{"detail": "transaction inconnue"}`
- `422` : identifiant qui n'est pas un UUID

### `GET /accounts/{iban_fake}`

Utilisé aussi par le script de vérification : le solde du compte de sonde doit rester suffisant.

```json
{
  "id": "…",
  "iban_fake": "TEST-0001",
  "balance_cents": 999900,
  "currency": "EUR"
}
```

- `404` : `{"detail": "compte inconnu : …"}`

### `GET /metrics`

Format texte Prometheus, produit par `prometheus-fastapi-instrumentator`. Les routes `/health` et `/metrics` sont exclues des métriques de latence. Les statuts sont regroupés (`2xx`, `4xx`, `5xx`), ce qu'exploite le dashboard Grafana (`status=~"5.*"`). Prometheus lit ce chemin sur `api:8000`.

## Authentification

Seule l'écriture (`POST /transactions`) est protégée, par un jeton partagé :

```
Authorization: Bearer <PROBE_TOKEN>
```

- Le jeton attendu vient de la variable d'environnement `PROBE_TOKEN`, la même que celle du moteur de remédiation (`services/remediation`).
- La comparaison se fait en temps constant (`hmac.compare_digest`).
- Jeton absent ou invalide : `401` `{"detail": "jeton invalide"}`.
- **Si `PROBE_TOKEN` est vide, la garde est désactivée.** Réservé au développement local, voir [Limites connues](#sécurité-et-limites-connues).
- Les routes de lecture et `/health` ne demandent pas de jeton.

Les utilisateurs finaux s'inscrivent et se connectent auprès du service `auth` (`services/auth`), qui émet un JWT HS256 `{sub, iat, exp}` signé avec `JWT_SECRET`. L'API vérifie ce jeton (algorithme figé à HS256, `sub` et `exp` requis) et expose l'espace client sous `/me`, joignable par la passerelle :

- `GET /me/account` : compte de l'utilisateur du jeton.
- `GET /me/transactions?limit=20` : historique (1..100), `direction` `debit`/`credit`.
- `POST /me/transfers` `{to_account, amount_cents, idempotency_key}` : la source est toujours le compte du jeton ; la clé d'idempotence est hachée avec l'identifiant utilisateur, un client ne peut donc pas rejouer la clé d'un autre.
- Jeton absent, invalide ou expiré : `401`.

Le contrat de la sonde (`POST /transactions` + `PROBE_TOKEN`) reste inchangé.

## Montants, devises et idempotence

- **Aucun `float` ne touche à de l'argent.** Les montants sont des entiers de centimes (`BIGINT` en base). La forme `amount` (unités) est convertie via `Decimal`, puis refusée si elle n'est pas un nombre entier de centimes.
- **Devise** : `EUR` par défaut. Un compte n'accepte que sa propre devise, sinon la transaction est rejetée (409).
- **Idempotence** : `idempotency_key` est unique en base (`uq_transactions_idempotency_key`). Rejouer la même clé ne débite jamais deux fois, ce dont dépend la sonde de reprise. Sans clé fournie, le serveur en génère une, donc chaque appel est une nouvelle transaction.
- **Concurrence** : les comptes sont lus avec `SELECT … FOR UPDATE`, pour que deux virements simultanés ne partent pas du même solde.

## Codes de réponse

| Code | Quand |
|---|---|
| `200` | Succès (virement réglé, lecture) |
| `401` | Jeton invalide ou absent sur `POST /transactions` |
| `404` | Compte ou transaction inconnu |
| `409` | Transaction **refusée** (solde insuffisant, devise) ou rejeu d'une transaction non réglée |
| `422` | Corps invalide : champs manquants, montant ≤ 0, les deux montants fournis, montant plus fin que le centime, devise de longueur ≠ 3, comptes identiques, UUID mal formé |
| `503` | `GET /health` : la base ne répond pas |

## Événements et métriques

### Logs JSON

Chaque étape écrit une ligne JSON sur `stdout`, collectée par Alloy puis envoyée à Loki :

```json
{
  "service": "api",
  "trace_id": "9f2c…",
  "event": "transaction.settled",
  "at": "2026-10-19T14:02:11.480112+00:00",
  "data": { "transaction_id": "…", "amount_cents": 100, "status": "settled" }
}
```

| `event` | Émis quand |
|---|---|
| `service.started` | Démarrage de l'API (`trace_id` = `boot`) |
| `transaction.received` | Virement reçu, avant exécution |
| `transaction.settled` | Virement réglé |
| `transaction.rejected` | Refus métier (`data.reason`) |
| `transaction.replayed` | Rejeu d'une clé d'idempotence |
| `transaction.unknown_account` | Compte inconnu (`data.account`) |

Aucun secret ni jeton n'est journalisé. Le `trace_id` est généré **par transaction** : attention à ne pas l'utiliser comme label Loki (cardinalité).

### Métriques

`/metrics` expose notamment `http_requests_total{method,handler,status}` et `http_request_duration_seconds_bucket{method,handler}`.

## Modèle de données

Schéma créé par la migration Alembic `0001_socle_initial` (détails et rôles dans [`services/db/README.md`](../db/README.md)).

| Table | Rôle |
|---|---|
| `users` | Utilisateurs fictifs (`customer`, `merchant`, `probe`, `admin`), mot de passe haché en argon2 |
| `merchants` | Marchands fictifs (code MCC, hachage de clé d'API) |
| `accounts` | Comptes : `iban_fake` unique, `balance_cents >= 0` |
| `transactions` | Virements : `status`, `idempotency_key` unique, `trace_id`, `amount_cents > 0`, comptes distincts |
| `ledger_entries` | Grand livre **en ajout seul** : un virement réglé produit un débit et un crédit, donc `SUM(debit) = SUM(credit)` |

Droits du rôle `app_rw` utilisé par l'API : `SELECT`, `INSERT`, `UPDATE`. Ni `DELETE`, ni DDL, ni `UPDATE` sur `ledger_entries`.

### Comptes de démonstration

Chargés par `scripts/seed_demo.py` (rechargés à chaque `scripts/reset_demo.sh`) :

| IBAN fictif | Titulaire | Solde initial |
|---|---|---|
| `TEST-0001` | compte de sonde (`probe@resilience.local`) | `PROBE_BALANCE_CENTS` (10 000,00 € par défaut) |
| `TEST-0002` | contrepartie de la sonde | 0 |
| `FR7630001007941234567890185` | alice | 2 500,00 € |
| `FR7630001007941234567890186` | bob | 1 200,00 € |
| `FR7630001007941234567890187` | boutique | 5 000,00 € |

**Ne pas renommer `TEST-0001` et `TEST-0002`** sans adapter la sonde du moteur de remédiation.

## Configuration

Lue uniquement dans `app/config.py`. Aucun secret dans le dépôt : valeurs réelles dans `.env` (ignoré par Git), modèle dans `.env.example`.

| Variable | Rôle | Défaut |
|---|---|---|
| `DATABASE_URL` | URL de connexion du rôle `app_rw` (`postgresql+asyncpg://…`) | obligatoire |
| `PROBE_TOKEN` | Jeton de l'écriture ; vide = garde désactivée | vide |
| `PROBE_ACCOUNT_IBAN` | IBAN du compte de sonde | `TEST-0001` |
| `JWT_SECRET` | Secret de vérification des jetons `/me/*` ; vide = aucun jeton accepté | vide |
| `DB_POOL_SIZE` | Taille du pool de connexions | `5` |
| `SQL_ECHO` | `1` pour journaliser le SQL (débogage) | `0` |

Les autres variables du `.env` (`POSTGRES_*`, `APP_RW_PASSWORD`, `APP_RO_PASSWORD`, `SEED_PASSWORD`, `PROBE_BALANCE_CENTS`) servent à PostgreSQL, aux migrations et au seed.

## Lancer, tester, vérifier

### Déploiement (depuis la racine du dépôt)

```bash
cp .env.example .env        # puis renseigner les secrets (Vault/SOPS)
docker compose --env-file .env -f infra/compose/docker-compose.yml up -d --wait --build
```

L'ordre est géré par Compose : `postgres` sain, puis `migrate` (migrations + seed, seul détenteur des droits DDL), puis `api`. L'option `--env-file` est obligatoire : PostgreSQL refuse de démarrer sans mots de passe.

### Tests unitaires

Sans PostgreSQL ni HTTP réel : doubles en mémoire pour les ports et client de test FastAPI.

```bash
cd services/api
pip install -r requirements.txt pytest anyio
python -m pytest -q
```

Un `pytest services/` depuis la racine échoue : les paquets `app` des services entrent en collision.

Qualité : `ruff check` et `ruff format` (ou `black`), ligne de 100 caractères, voir `pyproject.toml`.

### Preuve de vie et reset

```bash
./scripts/check_transaction.sh   # API saine + vraie transaction réglée (joué dans le conteneur api)
./scripts/reset_demo.sh          # schéma reconstruit, jeu de données rechargé, API recréée
```

La démonstration doit pouvoir être rejouée au moins cinq fois : enchaîner `reset_demo.sh` puis `check_transaction.sh`.

## Sécurité et limites connues

Conforme aux règles du projet : aucun port publié (seul le WAF/front le sera), conteneur sans privilèges (`cap_drop: ALL`, `no-new-privileges`), PostgreSQL sur un réseau interne, rôle à droits réduits. Une injection SQL réussie ne peut donc ni supprimer une table, ni effacer une ligne, ni réécrire une écriture comptable.

Limites relevées en relecture (suivi à prévoir) :

1. **Garde ouverte si `PROBE_TOKEN` est vide** : un oubli de configuration désactive l'authentification en silence. À remplacer par un échec au démarrage, avec une variable explicite pour le développement local.
2. **Lectures non authentifiées** : `GET /accounts/{iban}` et `GET /transactions/{id}` exposent les soldes à quiconque atteint l'API. Données fictives, mais à protéger avant la démo d'attaque.
3. **Interblocage possible** : les comptes sont verrouillés dans l'ordre source puis destination. Deux virements croisés A→B et B→A simultanés peuvent s'interbloquer ; trier les verrous par IBAN règle le cas.
4. **Course sur la clé d'idempotence** : deux requêtes simultanées avec la même clé peuvent faire échouer la seconde en `500` (violation d'unicité) au lieu de renvoyer la transaction existante.
5. **`/docs` et `/openapi.json`** sont actifs : à ne pas publier derrière le WAF.
6. Le `trace_id` est unique par transaction : à garder en métadonnée structurée Loki, jamais en label.

## Contrat avec le moteur de remédiation

La sonde (`services/remediation/app/adapters/api_probe.py`) envoie :

```json
{ "from_account": "TEST-0001", "to_account": "TEST-0002", "amount": 1.0 }
```

avec `Authorization: Bearer <PROBE_TOKEN>` si un jeton est configuré, sur `POST {API_BASE_URL}/transactions` (par défaut `http://api:8000`). Elle considère la reprise prouvée uniquement si la réponse est un **2xx**, d'où le `409` pour les refus. La vérification de santé appelle `GET /health`, qui renvoie `503` si la base est tombée.
