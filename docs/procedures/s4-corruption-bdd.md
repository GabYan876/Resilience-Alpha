# Procédure S4 — corruption de la base

Responsable : Antoine (BDD) avec Kevin (moteur). Statut : **procédure d'essai**, à jouer pour mesurer le
RPO et RTO. Le détecteur signale `database_corruption` tout seul (invariants du grand livre) ; le
`POST /incidents` manuel ne sert plus qu'à rejouer un cas particulier.

## Pré-requis

- `.env` complet (`PROBE_TOKEN`, `REMEDIATION_INGEST_TOKEN`), pile démarrée :
  `docker compose --env-file .env -f infra/compose/docker-compose.yml up -d --wait`.
- État propre : `./scripts/reset_demo.sh` (purge les archives, crée celle de l'état propre).
- Au moins une archive : `docker compose ... exec -T db-recovery ls /backups`.

## Déroulé

1. Noter l'heure `T0` et vérifier l'état : `./scripts/check_transaction.sh`.
2. **Corrompre** (données fictives) : par exemple, dans `postgres`, supprimer les transactions du compte de
   test avec le rôle propriétaire (`app_rw` n'a pas de `DELETE`). Noter l'heure `Tc`.
3. **Ne rien déclarer** : le détecteur lit `GET /integrity` toutes les 5 s et signale dès que les
   compteurs reculent. Variante manuelle (cas particulier) : `POST /incidents` du moteur avec le
   jeton d'ingestion et `kind=database_corruption` (corps : `services/remediation/app/api/schemas.py`).
   Une sauvegarde planifiée prise après `Tc` contiendrait la donnée altérée : c'est pour cela que la
   restauration ignore les archives postérieures à la détection.
4. Observer, sans intervenir : `incident.detected` → `action.executed` (`restore_database`, puis
   `restart_service`) → `verification.completed` → `incident.resolved`.

## Critères de réussite

- Incident `resolved` ; la transaction de sonde passe ; les données supprimées sont revenues.
- **RPO mesuré** = `Tc` − date de l'archive restaurée (champ `archive` de `database.restore.completed`).
  Cible ≤ 5 min.
- **RTO mesuré** = durée entre `Tc` (commit de la corruption, horodaté immédiatement après le `COMMIT`)
  et `incident.resolved`. Consigner aussi `incident.detected` → `incident.resolved` pour isoler la
  durée de remédiation.
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
- Ces 6 passages étaient semi-manuels (incident déclaré par `POST /incidents`) ; voir la section
  suivante pour le déclenchement automatique.

## Essai automatique du 20/10 (Kevin, Docker Desktop)

Aucun appel à `POST /incidents` : `DELETE` sur `ledger_entries` et `transactions`, puis observation.
Le détecteur (`IntegrityWatchService`) voit les compteurs reculer, signale `database_corruption`,
le moteur restaure l'archive antérieure à la détection, redémarre l'API et vérifie par transaction.

| Passage | Résultat | `incident.detected` → `incident.resolved` |
|---|---|---|
| 1 (corruption 17:23:21) | résolu, données revenues, aucune intervention | 17:23:22 → 17:23:27, soit ≈ 5 s |
| 2 à 5 | 4 × résolu, mêmes comptes avant/après (+ 1 transaction de sonde) | ≈ 5 s chacun |

Enseignement : `reset_demo.sh` vide les tables, ce que le détecteur prenait pour une corruption (une
restauration se déclenchait en plein reset). Le script met désormais le détecteur en pause puis le
relance à la fin : il réapprend sa référence sur la base propre.

## Essai sur pile complète du 21/10 (Antoine, pile locale jetable)

Même déclenchement automatique que l'essai ci-dessus (`DELETE` sur `ledger_entries` et `transactions`),
mais cette fois sur la pile complète (Compose socle + observabilité), pas la pile S4 isolée du 20/10.

| Passage | Résultat | RTO (`incident.detected` → `incident.resolved`) | RPO |
|---|---|---|---|
| 1 (08:20, Antoine) | résolu, API saine, transaction de sonde réussie | 3,79 s (détection 2,26 s + remédiation 1,53 s) | 59,32 s |
| 2 (13:36, Kevin, logs rejoués pour rafraîchir le dashboard Grafana) | résolu, API saine, transaction de sonde réussie | 3,24 s | 13,56 s |

Passage 1 : incident `d275a01df1484285a179c81723b06818` ; archive restaurée
`backup-20261021T081951.634330Z.dump` ; corruption notée `Tc` ≈ `08:20:50.949753Z`.
Passage 2 : incident `d0317683ecbe4d8b84d928269073ac62` ; archive restaurée datée
`2026-10-21T13:36:23.342566+00:00` ; corruption notée `Tc` ≈ `13:36:36.900325Z`.

Deux passages (toujours pas une garantie statistique) : ne remplacent pas les 6 passages du 20/10, les
complètent sur une pile représentative de la démo réelle. Le RPO varie avec l'écart naturel jusqu'à la
dernière sauvegarde planifiée (300 s d'intervalle), pas un écart imposé comme le 20/10 : le pire cas
théorique reste l'intervalle de sauvegarde (300 s) + la marge (15 s) ≈ 5 min 15 s, toujours légèrement
au-dessus de la cible de 5 min. Reporté dans `docs/gouvernance/02-pca-pra.md` §2/§3/§7/§8.

## Rejeu S4 dans le contexte chaos du 22/10 (pile locale jetable)

Un passage automatique a été exécuté sur une pile S4 dédiée : PostgreSQL, API, `db-recovery`,
remédiation et détecteur, avec Prometheus et Loki démarrés. Les projets Compose, conteneurs,
réseaux et volumes portaient tous le préfixe `ra-s4-chaos-20261022` ; aucun volume ou réseau
de la pile active (`resilience-alpha`) ni de `website` n'était monté ou rejoint. L'injection
visait uniquement ce conteneur PostgreSQL jetable. Le WAF, Alloy et Grafana n'ont pas été lancés :
ce passage valide le scénario S4 automatisé, pas une attaque depuis le PC Attaquant ni la collecte
des journaux dans Loki.

Avant l'injection, la transaction de référence a réussi ; l'intégrité comptait 1 transaction et
2 écritures équilibrées. L'archive propre `backup-20261022T113339.759793Z.dump` a été créée,
puis la corruption a été appliquée aux deux tables fictives (`DELETE 2` dans `ledger_entries`,
`DELETE 1` dans `transactions`). `Tc`, relevé immédiatement après le commit, est
`2026-10-22T11:35:28.536602Z`.

| Passage | Incident / résultat | RTO (`Tc` → `incident.resolved`) | RPO (`Tc` − archive restaurée) |
|---|---|---|---|
| 1 (22/10, pile S4 jetable) | détection automatique ; restauration et redémarrage réussis ; API saine et transaction de sonde réussie | **6,376839 s** (détection : 4,826715 s ; `incident.detected` → résolution : 1,550124 s) | **108,776809 s** |

Preuves : incident `719c01d79127434898a87be13d2bdb5f` ; `incident.detected` à
`11:35:33.363317Z` (`source=db-recovery:integrity`), `database.restore.completed` avec
`backup-20261022T113339.759793Z.dump`, `verification.completed` à `11:35:34.913408Z`
(`api_healthy=true`, `probe_transaction_ok=true`) et `incident.resolved` à
`11:35:34.913441Z`. Après la restauration et la sonde intégrée, une vérification explicite
supplémentaire a également réussi (`OK santé + transaction réglée (100 centimes)`), avec
3 transactions, 6 écritures et 0 transaction déséquilibrée. Les événements viennent des journaux
JSON stdout horodatés des conteneurs isolés ; Alloy n'étant pas lancé, ils ne sont pas présentés
comme des preuves Loki.

Le RTO est calculé entre `Tc` et `incident.resolved.at` ; le RPO entre `Tc` et l'horodatage UTC
dans le nom de l'archive effectivement restaurée. Ce passage unique confirme le mécanisme mais
ne constitue pas une garantie statistique. Résultats reportés dans
[`../gouvernance/02-pca-pra.md`](../gouvernance/02-pca-pra.md) §2/§3/§5/§7/§8.
