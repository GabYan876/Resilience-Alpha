# PCA / PRA — Resilience-Alpha

Statut : première version du 20/10 (RTO/RPO provisoires, à valider). Responsable : Antoine. Valeurs RTO/RPO : mesurées par Kevin lors des essais.

## 1. Périmètre et hypothèses
- Hébergement : PC Hôte unique (Docker Compose). Pas de site de secours réel : à écrire comme limite.
- Services couverts : front, API métier, auth, BDD, WAF, moteur de remédiation, observabilité.

## 2. Scénarios couverts

| ID | Scénario | Type | Réponse | Automatique ? |
|---|---|---|---|---|
| S1 | Flood sur l'API | Disponibilité | Blocage IP + restart + vérif transaction | Oui (Zero-Touch) |
| S2 | SQLi / exfiltration | Compromission | Blocage IP + rotation des secrets + vérif transaction ; **investigation manuelle** (on ne peut pas prouver l'absence de fuite) | Partielle : automatique sauf l'investigation |
| S3 | Crash d'un conteneur | Disponibilité | Détection par health check périodique (`HealthWatchDetector` dans le moteur), restart + vérif | Oui (essai réel du 20/10 : arrêt de l'API, reprise en 34 s) |
| S4 | Perte de la BDD / corruption | Données | `RestoreDatabaseAction` (restauration de sauvegarde) + vérif transaction | Oui (cible ; action à développer) |
| S5 | Perte du PC Hôte | Site | Hors périmètre démontrable | Non |

Distinguer **restauration de disponibilité** (S1, S3) et **correction de compromission** (S2) : les actions sont différentes.

État d'avancement (20/10) : le pipeline couvre S1 (blocage de la source par IP et compte, redémarrage, vérification) et S3 (sondage de santé) dans `services/remediation/`. Restent à développer : `VaultSecretRotator` (S2), `RestoreDatabaseAction` (S4, droits élevés sur la BDD à encadrer). Tant qu'ils n'existent pas, ces scénarios ne sont **pas** automatiques : le moteur déclare l'incident en échec plutôt que résolu.

## 3. Objectifs de continuité et de reprise

| Service | Criticité | RTO cible | RTO mesuré | RPO cible | RPO mesuré | Source de la mesure |
|---|---|---|---|---|---|---|
| Paiement (API + auth + BDD) | Critique | 60 s (proposition) | Flood : 33-48 s (moyenne 45 s, 5/5) ; crash : 34 s | À DÉFINIR avec la sauvegarde (S4) | Non mesurable : aucune sauvegarde | Événements JSON de remédiation (Loki) |
| Dashboard (Grafana) | Importante | 5 min (proposition) | À MESURER | Sans objet (provisionné par fichiers) | Sans objet | |
| Observabilité | Importante : sans elle la détection est aveugle | 5 min (proposition) | À MESURER | Logs perdus pendant l'arrêt | À MESURER | |

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
Stratégie de sauvegarde (fréquence, lieu, chiffrement), restauration de la BDD (via `RestoreDatabaseAction`, S4), rejouabilité (script de reset d'état). Le RPO cible découle de la fréquence de sauvegarde. À DÉFINIR avec Hugo et Antoine.

## 6. Procédures
Les procédures opérationnelles vont dans `docs/procedures/`. Une procédure par scénario.

## 7. Essais et preuves
Chaque essai : date, scénario, résultat, RTO observé, intervention humaine (oui/non), lien vers log ou capture.

| Date | Scénario | Résultat | RTO observé | Intervention humaine | Preuve |
|---|---|---|---|---|---|
| 20/10 | S1 flood, 5 passages (`scripts/demo_loop.py`) | 5/5 reprises, vérifiées par transaction de test | 33-48 s (moyenne 45 s) | Non | Événements `incident.*` dans Loki |
| 20/10 | S3 crash de l'API | Reprise automatique | 34 s (détection ~30 s) | Non | Événements `incident.*` (kind `crash`) dans Loki |

Objectif : ≥ 5 passages sans intervention.

## 8. Risques qui subsistent après la reprise
- **Attaquant qui revient** : bloqué par compte, il peut en créer un autre ; sous Docker Desktop l'IP n'est pas distinguée.
- **Secret compromis non détecté** : rotation codée mais sans Vault/SOPS ; secrets dans `.env`.
- **Données** : aucune sauvegarde, donc S4 et le RPO ne sont pas tenus.
- **SPOF** : un seul PC Hôte (S5 hors périmètre).
- **Faux positif ML** : 0 sur 120 mesures de trafic inédit, mais le score sature et le seuil reste à recalibrer sur trafic réel.
