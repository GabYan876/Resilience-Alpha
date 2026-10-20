# Procédure S4 — corruption de la base

Responsable : Antoine (BDD) avec Kevin (moteur). Statut : **procédure d'essai**, à jouer pour mesurer le
RPO ; le déclencheur reste manuel tant qu'aucun détecteur ne signale `database_corruption`.

## Pré-requis

- `.env` complet (`PROBE_TOKEN`, `REMEDIATION_INGEST_TOKEN`), pile démarrée :
  `docker compose --env-file .env -f infra/compose/docker-compose.yml up -d --wait`.
- État propre : `./scripts/reset_demo.sh` (purge les archives, crée celle de l'état propre).
- Au moins une archive : `docker compose ... exec -T db-recovery ls /backups`.

## Déroulé

1. Noter l'heure `T0` et vérifier l'état : `./scripts/check_transaction.sh`.
2. **Corrompre** (données fictives) : par exemple, dans `postgres`, supprimer les transactions du compte de
   test avec le rôle propriétaire (`app_rw` n'a pas de `DELETE`). Noter l'heure `Tc`.
3. Déclarer l'incident (équivalent du détecteur) rapidement : une sauvegarde planifiée prise après `Tc`
   contiendrait la donnée altérée. `POST /incidents` du moteur avec le jeton d'ingestion et
   `kind=database_corruption` (corps : `services/remediation/app/api/schemas.py`).
4. Observer, sans intervenir : `incident.detected` → `action.executed` (`restore_database`, puis
   `restart_service`) → `verification.completed` → `incident.resolved`.

## Critères de réussite

- Incident `resolved` ; la transaction de sonde passe ; les données supprimées sont revenues.
- **RPO mesuré** = `Tc` − date de l'archive restaurée (champ `archive` de `database.restore.completed`).
  Cible ≤ 5 min.
- **RTO mesuré** = durée entre `incident.detected` et `incident.resolved`.
- Aucune intervention humaine pendant l'étape 4.

## Échecs attendus (à ne pas masquer)

- Aucune archive antérieure à la détection : `incident.failed`, raison `required_action_failed`. Une API
  saine ne suffit pas à clore l'incident.
- Corruption plus ancienne que la marge (`DB_RESTORE_SAFETY_MARGIN_S`) : l'archive restaurée peut être
  altérée. Limite connue, non traitée.

## Remise à zéro

`./scripts/reset_demo.sh`, puis rejouer. Reporter RPO et RTO dans `docs/gouvernance/02-pca-pra.md`
(section 3).
