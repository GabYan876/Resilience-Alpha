# Socle base de données — PostgreSQL + Alembic

Schéma et migrations de la plateforme de paiement fictive. Les modèles SQLAlchemy
vivent dans `services/api/app/adapters/persistence/models.py` : ce dossier ne
contient que la configuration Alembic, qui s'y branche pour détecter les écarts.

> Données 100 % fictives. Aucune donnée bancaire réelle, aucun secret en clair.

## Schéma

| Table | Rôle | Points d'attention |
|---|---|---|
| `users` | comptes applicatifs | `email` unique, `password_hash` en argon2 |
| `merchants` | marchands | `mcc` à 4 chiffres, seul le hachage de la clé d'API est stocké |
| `accounts` | comptes de paiement | `balance_cents` en `BIGINT`, contrainte `>= 0` |
| `transactions` | virements | `amount_cents` en `BIGINT`, `idempotency_key` unique, `trace_id` |
| `ledger_entries` | grand livre | double entrée : un virement réglé produit un `debit` et un `credit` |

**Les montants sont des entiers de centimes.** Aucun `float` ne touche à de
l'argent : `0.1 + 0.2 != 0.3` suffirait à rendre la comptabilité indéfendable
devant le jury.

Vérification de l'équilibre comptable :

```sql
SELECT direction, SUM(amount_cents) FROM ledger_entries GROUP BY direction;
-- les deux lignes doivent être égales
```

## Rôles PostgreSQL (durcissement)

La migration initiale crée deux rôles applicatifs, en plus du rôle propriétaire :

| Rôle | Droits | Utilisé par |
|---|---|---|
| propriétaire (`POSTGRES_USER`) | DDL complet | migrations Alembic (service `migrate` uniquement) |
| `app_rw` | `SELECT`, `INSERT`, `UPDATE` ; ni DDL, ni `DELETE`, ni `UPDATE` sur `ledger_entries` | API métier |
| `app_ro` | `SELECT` | assistant RAG (lecture seule) |

Conséquence : une injection SQL réussie contre l'API ne peut ni supprimer une
table, ni effacer une ligne, ni réécrire une écriture comptable. L'assistant RAG,
lui, n'a aucun droit d'écriture.

Les mots de passe des rôles ne sont jamais interpolés dans le SQL : ils passent
par un paramètre lié puis par un réglage de session (`set_config` /
`current_setting`), donc ils n'apparaissent pas dans les journaux PostgreSQL.
En mode hors connexion (`alembic upgrade head --sql`), la création des rôles est
remplacée par un commentaire : un fichier SQL ne doit pas contenir de secret.

## Commandes

Les migrations ne s'exécutent que depuis le service `migrate` (le seul à détenir
les identifiants du rôle propriétaire) :

```bash
# Déploiement complet : migrate s'exécute avant l'API
docker compose --env-file .env -f infra/compose/docker-compose.yml up -d --wait

# Remise à zéro rejouable (schéma reconstruit + jeu de données rechargé)
./scripts/reset_demo.sh

# Preuve de vie : API saine + vraie transaction réglée
./scripts/check_transaction.sh
```

En local, hors conteneur (depuis `services/db/`) :

```bash
export DATABASE_URL_ADMIN=postgresql+asyncpg://owner:motdepasse@localhost:5432/resilience
export APP_RW_PASSWORD=... APP_RO_PASSWORD=...
alembic -c alembic.ini upgrade head
alembic -c alembic.ini upgrade head --sql   # relire le DDL sans l'appliquer
alembic -c alembic.ini revision -m "ajout de ..."
```

L'URL est toujours lue dans l'environnement (`DATABASE_URL_ADMIN`, à défaut
`DATABASE_URL`) : `alembic.ini` ne contient aucun identifiant.

Attention au pilote : l'URL est en `postgresql+asyncpg://`. `asyncpg` ne connaît
pas le paramètre libpq `sslmode` ; l'équivalent est `ssl`.

## Compte de sonde (critique pour la démonstration)

Le moteur de remédiation prouve la reprise en jouant une **vraie** transaction
(`services/remediation/app/adapters/api_probe.py`) :

- utilisateur `probe@resilience.local` ;
- compte source `TEST-0001`, destinataire `TEST-0002` ;
- solde rechargé à `PROBE_BALANCE_CENTS` (10 000,00 € par défaut) à chaque
  exécution de `scripts/reset_demo.sh`.

Sans cette recharge, la sonde finirait par échouer pour solde insuffisant après
quelques passages et l'on conclurait à tort à une panne de la plateforme. Les
identifiants `TEST-0001` / `TEST-0002` sont le contrat avec le moteur de
remédiation : ne pas les renommer sans adapter la sonde.

## Rejouabilité

`scripts/reset_demo.sh` enchaîne `alembic downgrade base`, `alembic upgrade head`
puis `scripts/seed_demo.py`. Le seed est idempotent (UPSERT) et les identifiants
sont déterministes (UUID v5), donc l'état de la base est identique à chaque
passage : la démonstration peut être rejouée au moins cinq fois sans intervention.

Deux pièges réglés, à ne pas réintroduire — ils se manifestent uniquement contre
un vrai PostgreSQL, jamais en test unitaire :

- **Le pool de l'API doit être recréé après chaque reset.** `downgrade` supprime
  les rôles `app_rw` / `app_ro`, `upgrade` les recrée avec de nouveaux OID, et les
  connexions encore ouvertes restent authentifiées sous les anciens : la première
  transaction échoue en `permission denied for table transactions`. Le
  `pool_pre_ping` ne le détecte pas, son `SELECT 1` ne déclenchant aucun contrôle
  d'ACL. D'où le `up -d --force-recreate --no-deps api` en fin de script : un
  simple `up -d` ne touche pas un conteneur déjà sain.
- **Les caches de requêtes préparées sont désactivés** dans `build_engine`
  (`prepared_statement_cache_size=0` côté dialecte, `statement_cache_size=0` côté
  asyncpg). Reconstruire tables et types ENUM sous un pool ouvert invalide les
  plans en cache, et la requête suivante échoue en `InvalidCachedStatementError`.
