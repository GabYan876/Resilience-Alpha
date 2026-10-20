# db-recovery

Service privé de sauvegarde et de restauration PostgreSQL (scénario S4, corruption de la base).
Il ne décide rien : le moteur de remédiation l'appelle pour un incident `database_corruption`,
puis prouve la reprise par une transaction de sonde. Contexte et limites : [`../README.md`](../README.md).

## Fonctionnement

```
tâche planifiée (au démarrage, puis toutes les DB_BACKUP_INTERVAL_S)
        └─> DatabaseRecoveryService ──> PostgresArchiveStore ──> pg_dump --format=custom ──> /backups
remediation ── POST /restore?before=<date> ──> pg_restore --clean --single-transaction
```

- Archives `backup-<AAAAMMJJ>T<HHMMSS.µs>Z.dump` dans le volume `postgres-backups`, mode `0600`,
  écrites en fichier temporaire puis renommées (jamais d'archive à moitié écrite).
- Les `DB_BACKUP_RETENTION` plus récentes sont conservées.
- Restauration : `pg_restore --list` valide l'archive, puis restauration dans **une seule transaction**
  (un échec laisse la base inchangée). Avec `before`, seules les archives **strictement antérieures**
  sont candidates ; sans archive éligible, la route répond `503` et le moteur déclare l'incident en échec.
- Sauvegarde et restauration sont sérialisées (verrou) : pas de restauration pendant un dump.

## Routes (réseau `control-internal`, aucun port publié)

| Route | Jeton | Effet |
|---|---|---|
| `GET /health` | non | `200` si PostgreSQL répond **et** qu'au moins une archive existe, sinon `503` |
| `GET /integrity` | non | compteurs `{transactions, ledger_entries, unbalanced_transactions}`, aucune donnée (lu par le détecteur) |
| `POST /backup` | `Bearer $PROBE_TOKEN` | crée une archive, renvoie `{"status","archive"}` |
| `POST /restore[?before=<ISO 8601>]` | `Bearer $PROBE_TOKEN` | restaure la dernière archive éligible |

Jeton absent ou faux : `401`. Comparaison en temps constant.

## Configuration (`app/config.py`, seul lecteur de l'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `PROBE_TOKEN` | obligatoire | jeton partagé avec la sonde du moteur |
| `POSTGRES_PASSWORD` | obligatoire | mot de passe du rôle propriétaire (droits de restauration) |
| `POSTGRES_DB`, `POSTGRES_USER`, `PGHOST`, `PGPORT` | `resilience`, `resilience_owner`, `postgres`, `5432` | cible PostgreSQL |
| `DB_BACKUP_PATH` | `/backups` | dossier des archives |
| `DB_BACKUP_INTERVAL_S` | `300` | période de sauvegarde (cible RPO) |
| `DB_BACKUP_RETENTION` | `12` | nombre d'archives gardées |

La marge appliquée au `before` (`DB_RESTORE_SAFETY_MARGIN_S`) est lue par le **moteur**, pas par ce service.

## Événements JSON (stdout, collectés par Alloy vers Loki)

`{"service":"db-recovery","trace_id","event",…}` avec `event` parmi `database.backup.created`,
`database.backup.failed`, `database.restore.completed`, `database.restore.failed`. Le nom de
l'archive est journalisé, jamais un secret.

## Sécurité

Conteneur `read_only`, `cap_drop: ALL`, `no-new-privileges`, utilisateur `postgres`, 128 Mo. Il détient
le rôle propriétaire de la base : c'est le seul composant avec ces droits en dehors de `migrate`, d'où
le réseau interne et le jeton. Archives non chiffrées, sur le même hôte : voir les limites du README parent.

## Tests

```bash
cd services/db/recovery && python -m pytest -q
```

Le domaine et les routes sont testés sans PostgreSQL (faux `subprocess`, fausse archive).
Restauration réelle : voir [`docs/procedures/s4-corruption-bdd.md`](../../../docs/procedures/s4-corruption-bdd.md).
