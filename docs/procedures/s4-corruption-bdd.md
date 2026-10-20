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

## Essai réel du 20/10 (Kevin, Docker Desktop, pile S4 seule)

Déclenchement manuel (`POST /incidents`, `kind=database_corruption`) ; corruption = `DELETE` sur
`ledger_entries` et `transactions` avec le rôle propriétaire ; archive prise 20 s avant la corruption.

| Passage | Cas | Résultat | RTO (`incident.detected` → `incident.resolved`) |
|---|---|---|---|
| 1 | marge 60 s (ancien défaut), reset < 60 s avant | **échec voulu** : aucune archive éligible, `503 backup_unavailable`, `incident.failed` | — |
| 2 | marge 15 s | résolu, 3 transactions + 1 de sonde revenues | 4,7 s |
| 3 | archive prise **après** la corruption (Tc + 7 s) | résolu, l'archive postérieure est ignorée, données saines restaurées | ≈ 5 s |
| 4 à 6 | marge 15 s, après `reset_demo.sh` | 3 × résolu, mêmes comptes avant/après | ≈ 5 s |

Enseignements :
- Une marge de 60 s est trop grande : elle exclut les archives récentes et dégrade le RPO. Défaut ramené à
  15 s (3 confirmations × 5 s du détecteur).
- **RPO mesuré : 20 s** ici, mais c'est l'écart que j'ai imposé entre archive et corruption. Dans le pire cas
  il vaut l'intervalle de sauvegarde (300 s) **plus** la marge (15 s) : environ 5 min 15 s, soit juste au-dessus de la
  cible de 5 min. Pour la tenir strictement, passer `DB_BACKUP_INTERVAL_S` à 240.
- Le déclencheur automatique (détecteur ML) n'est pas couvert : l'essai est semi-manuel.
