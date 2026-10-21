# PCA / PRA — Resilience-Alpha

Statut : mise à jour du 21/10 ; S4 mesuré sur la pile complète locale jetable, autres RTO/RPO à valider. Responsable : Antoine. Valeurs mesurées par Kevin lors des essais.

## 1. Périmètre et hypothèses
- Hébergement : PC Hôte unique (Docker Compose). Pas de site de secours réel : à écrire comme limite.
- Services couverts : front, API métier, auth, BDD, WAF, moteur de remédiation, observabilité.

## 2. Scénarios couverts

| ID | Scénario | Type | Réponse | Automatique ? |
|---|---|---|---|---|
| S1 | Flood sur l'API | Disponibilité | Blocage IP + restart + vérif transaction | Oui (Zero-Touch) |
| S2 | SQLi / exfiltration | Compromission | Blocage IP + rotation des secrets + vérif transaction ; **investigation manuelle** (on ne peut pas prouver l'absence de fuite) | Partielle : automatique sauf l'investigation |
| S3 | Crash d'un conteneur | Disponibilité | Détection par health check périodique (`HealthWatchDetector` dans le moteur), restart + vérif | Oui (essai réel du 20/10 : arrêt de l'API, reprise en 34 s) |
| S4 | Perte de la BDD / corruption | Données | Incident `DATABASE_CORRUPTION` : `RestoreDatabaseAction` + redémarrage API + vérif transaction | Essai automatique le 21/10 sur pile complète locale jetable : 2/2 reprises, RTO 3,24-3,79 s du commit de corruption à `incident.resolved`, RPO 13,56-59,32 s ; API saine et transaction de sonde réussie à chaque passage. Limite : une altération qui garde compteurs et équilibre n'est pas vue |
| S5 | Perte du PC Hôte | Site | Hors périmètre démontrable | Non |

Distinguer **restauration de disponibilité** (S1, S3) et **correction de compromission** (S2) : les actions sont différentes.

État d'avancement (21/10) : le pipeline couvre S1 (blocage de la source par IP et compte, redémarrage, vérification) et S3 (sondage de santé) dans `services/remediation/`. S4 dispose d'une sauvegarde planifiée et d'une restauration via le service privé `db-recovery`, protégée par `PROBE_TOKEN`, puis prouvée par une transaction. Le type distinct `DATABASE_CORRUPTION` empêche de confondre une altération de données avec une exfiltration. Le détecteur a signalé automatiquement `database_corruption` lors de deux essais sur la pile complète locale jetable le 21/10 (voir `docs/procedures/s4-corruption-bdd.md`) : RTO 3,24 s et 3,79 s du commit à la résolution, RPO 13,56 s et 59,32 s (l'écart vient du moment de la corruption dans le cycle de sauvegarde de 300 s, pas d'une différence de comportement). Avec l'intervalle de sauvegarde de 300 s et la marge de 15 s, le pire cas théorique reste ≈315 s, donc au-dessus de la cible de 5 min. S2 (rotation de secrets via `SopsSecretRotator`) est maintenant codée, testée et essayée en réel (§7) ; seule l'investigation manuelle de S2 reste non automatisée (assumé, voir §2).

## 3. Objectifs de continuité et de reprise

| Service | Criticité | RTO cible | RTO mesuré | RPO cible | RPO mesuré | Source de la mesure |
|---|---|---|---|---|---|---|
| Paiement (API + auth + BDD) | Critique | 60 s (proposition) | Flood : 33-48 s (moyenne 45 s, 5/5) ; crash : 34 s ; flood via WAF depuis PC Attaquant : 5,4-7,9 s de temps de remédiation seul (5/5, 21/10, détection non chronométrée) ; S4 : 3,24-3,79 s commit→résolution (2 passages) | ≤ 5 min (objectif) | S4 : 13,56-59,32 s sur la pile complète (2 passages) ; pire cas configuré ≈315 s (300 s + marge 15 s), supérieur à l'objectif | Événements JSON de remédiation et `database.restore.completed` dans Loki |
| Dashboard (Grafana) | Importante | 5 min (proposition) | 6-10 s (3 essais, arrêt brutal puis démarrage jusqu'à `healthy`) | Sans objet (provisionné par fichiers) | Sans objet | Mesure du 20/10 (Kevin), `docker kill` puis `docker start` |
| Observabilité | Importante : sans elle la détection est aveugle | 5 min (proposition) | Prometheus 6-8 s, Loki 22-24 s (3 essais chacun) | Logs perdus pendant l'arrêt | Non mesuré : la perte de logs pendant l'arrêt de Loki reste à quantifier | Mesure du 20/10 (Kevin), même méthode ; aucune règle de remédiation ne redémarre ces services, seul `restart: unless-stopped` s'en charge |

Définition de la reprise : **API saine ET transaction de test réussie** (pas seulement un conteneur relancé).

Mesure du RTO (décision du 19/10) : **début d'attaque → `incident.resolved`**. Le début d'attaque vient du journal horodaté du script d'attaque ; la fin, de l'événement `incident.resolved` dans Loki. On décompose aussi le délai de détection (début d'attaque → `incident.detected`) et le temps de remédiation (`incident.detected` → `incident.resolved`).

## 4. Responsabilités

Pendant l'incident, **aucune intervention humaine** (Zero-Touch). Les rôles décrivent ce que l'équipe fait après (proposition à valider).

| Rôle | Qui | Responsabilité après l'incident |
|---|---|---|
| Pilotage / décision | Kevin | Relit les événements, confirme la clôture, ajuste le seuil ML |
| Infra / WAF | Hugo | Vérifie le WAF et les réseaux, exécute le script de reset d'état |
| Backend / BDD | Antoine | Contrôle l'intégrité de la BDD et la restauration |
| Front / dashboard Grafana | Gabriel | Vérifie le front de paiement et l'affichage Grafana avant / pendant / après |
| Investigation / red team | François | Investigue S2 (fuite éventuelle), rapporte l'attaque jouée |

## 5. Choix de restauration
`db-recovery` produit des archives custom-format PostgreSQL toutes les 300 s et conserve les 12 dernières dans le volume Compose `postgres-backups`. La restauration choisit la dernière archive valide **antérieure à la détection** (moins une marge de 15 s), car une sauvegarde planifiée après la corruption contiendrait déjà la donnée altérée ; le moteur redémarre l'API et ne clôt l'incident qu'après une transaction de sonde authentifiée. Essais complets locaux jetables du 21/10 (2 passages) : RPO mesuré 59,32 s (horodatage relevé juste après le commit de corruption : 08:20:50.949753Z ; archive restaurée `backup-20261021T081951.634330Z.dump`) puis 13,56 s (corruption ≈ 13:36:36.900325Z ; archive datée 13:36:23.342566Z) ; RTO respectivement 3,79 s et 3,24 s jusqu'à `incident.resolved`. Le pire cas théorique avec la configuration actuelle est ≈315 s, légèrement supérieur à la cible de 5 min. Limites : volume sur le même PC Hôte, archives non chiffrées, donc aucune protection contre la perte de l'hôte/volume ; archives utilisables uniquement avec les données fictives de la démonstration.

## 6. Procédures
Les procédures opérationnelles vont dans `docs/procedures/`. Une procédure par scénario.

## 7. Essais et preuves
Chaque essai : date, scénario, résultat, RTO observé, intervention humaine (oui/non), lien vers log ou capture.

| Date | Scénario | Résultat | RTO observé | Intervention humaine | Preuve |
|---|---|---|---|---|---|
| 20/10 | S1 flood, 5 passages (`scripts/demo_loop.py`) | 5/5 reprises, vérifiées par transaction de test | 33-48 s (moyenne 45 s) | Non | Événements `incident.*` dans Loki |
| 20/10 | S3 crash de l'API | Reprise automatique | 34 s (détection ~30 s) | Non | Événements `incident.*` (kind `crash`) dans Loki |
| 21/10 | S4 corruption BDD, pile complète locale jetable, passage 1 (08:20, Antoine) | Restauration automatique ; API saine et transaction de sonde réussie | 3,79 s commit→résolution (détection 2,26 s ; remédiation 1,53 s) | Non | Loki, incident `d275a01df1484285a179c81723b06818` ; archive restaurée `backup-20261021T081951.634330Z.dump` ; RPO 59,32 s |
| 21/10 | S4 corruption BDD, pile complète locale jetable, passage 2 (13:36, Kevin, rejoué pour rafraîchir le dashboard Grafana) | Restauration automatique ; API saine et transaction de sonde réussie | 3,24 s commit→résolution | Non | Loki, incident `d0317683ecbe4d8b84d928269073ac62` ; archive restaurée datée `2026-10-21T13:36:23.342566+00:00` ; RPO 13,56 s |
| 21/10 | S1 flood, 5 passages depuis le **PC Attaquant**, à travers le WAF, `scripts/reset_demo.sh` rejoué entre chaque passage | 5/5 reprises (`block_subject` + `restart_service`), vérifiées par transaction de test | `incident.detected` → `incident.resolved` : 5,4 / 7,1 / 6,6 / 7,0 / 7,9 s (temps de remédiation seul ; délai de détection non mesuré ici, faute du journal horodaté du script d'attaque sur le PC Attaquant) | Non | Événements `incident.*` dans Loki/`resilience-remediation` ; `block_subject` vérifié par le blocage effectif (403) des requêtes suivantes dans les logs WAF |
| 21/10 | Faux positifs ML, trafic de fond (`scripts/background_traffic.py`, 2907 requêtes, 0 erreur) **à travers le WAF actif** (`192.168.1.140:8080`), 11 min, 120 mesures collectées (`ml/data/holdout_waf.csv`) | 0/120 mesures jugées anormales (0,0 %), aucun `incident.*` parasite dans les logs `resilience-anomaly-detector`/`resilience-remediation` pendant la fenêtre ; attaque toujours détectée sur `attack.csv` (75 %, alerte dès la mesure 5) | Sans objet (pas d'incident) | Non | `app.cli evaluate --normal /data/holdout_waf.csv --attack /data/attack.csv` ; `docker logs resilience-anomaly-detector/-remediation --since 15m` vides de tout `incident` |
| 21/10 | S2 SQLi (`attack/sqli_injection.py`), 6 charges classiques (`' OR 1=1 --`, `UNION SELECT`, `DROP TABLE`…) contre `/auth/login` (champ email, sans jeton) puis `/me/transfers` (champ `to_account`, avec jeton), **à travers le WAF** (`192.168.1.140:8080`) | 12/12 bloquées (403), règle CRS 942100 « SQL Injection Attack Detected via libinjection » déclenchée à chaque fois (score d'anomalie ≥ 8), confirmé présent dans Loki via le proxy Grafana (`datasources/proxy/uid/loki`) | Sans objet (bloqué en périmètre, pas d'incident `remediation`) | Non | Logs `resilience-waf` (`docker logs resilience-waf --since 5m \| grep 942100`) et requête Loki `{container="resilience-waf"} \|= "942100"` |
| 21/10 | S2 compromission, déclenchée manuellement (`POST /incidents kind=compromise`, pas encore depuis un signal SQLi réel) sur la pile complète locale | `RotateSecretAction`/`SopsSecretRotator` tourne `JWT_SECRET` (`infra/secrets/jwt.enc.yaml` et volume partagé `jwt-secret-live` cohérents, différents de la valeur d'environnement d'origine), `auth` et `api` redémarrés, `incident.resolved` | Sans objet (déclenchement manuel, pas de mesure de détection) | Non | `infra/secrets/jwt.enc.yaml` (valeur chiffrée changée), fichier live comparé sur `auth`/`api`, transaction de sonde réglée après coup |

Objectif : ≥ 5 passages sans intervention — **atteint le 21/10** depuis le PC Attaquant, à travers le WAF.

`block_ip` échoue systématiquement (« aucune IP source identifiée ») sur les 5 passages, `block_subject` seul agit — confirme, sans le contredire, l'arbitrage du 20/10 (`06-pilotage-arbitrages.md` ligne 40) : sous Docker Desktop, le WAF voit la passerelle Docker (`172.25.0.1`) pour tout le trafic LAN, attaquant ou légitime, donc `attacker_ip` n'est volontairement jamais renseigné par le détecteur (`detection.py`) et un blocage par IP couperait tout le monde. Ce n'est pas une régression à corriger ; voir `validation-jalon-21-10.md` §2.

## 8. Risques qui subsistent après la reprise
- **Attaquant qui revient** : bloqué par compte, il peut en créer un autre ; sous Docker Desktop l'IP n'est pas distinguée.
- **Secret compromis non détecté** : rotation codée, testée et essayée en réel via SOPS/age (§7) ; reste déclenchée manuellement (`POST /incidents kind=compromise`), pas encore par un détecteur de compromission automatique.
- **Données** : sauvegardes locales non chiffrées et non répliquées ; S4 vise la corruption logique, pas la perte du PC Hôte. RPO mesuré à 13,56 s et 59,32 s sur deux passages complets ; le pire cas théorique de 315 s dépasse encore l'objectif de 5 min.
- **SPOF** : un seul PC Hôte (S5 hors périmètre).
- **Faux positif ML** : 0 sur 120 mesures de trafic inédit (20/10, sans WAF) et de nouveau 0 sur 120 le 21/10 avec le WAF actif (§7), mais le score sature et le seuil reste à recalibrer sur trafic réel prolongé.
