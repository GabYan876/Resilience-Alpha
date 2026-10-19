# PCA / PRA — Resilience-Alpha

Statut : squelette. Responsable : Antoine. Valeurs RTO/RPO : mesurées par Kevin lors des essais.

## 1. Périmètre et hypothèses
- Hébergement : PC Hôte unique (Docker Compose). Pas de site de secours réel : à écrire comme limite.
- Services couverts : front, API métier, auth, BDD, WAF, moteur de remédiation, observabilité.

## 2. Scénarios couverts

| ID | Scénario | Type | Réponse | Automatique ? |
|---|---|---|---|---|
| S1 | Flood sur l'API | Disponibilité | Blocage IP + restart + vérif transaction | Oui (Zero-Touch) |
| S2 | SQLi / exfiltration | Compromission | Blocage IP + rotation des secrets + vérif transaction ; **investigation manuelle** (on ne peut pas prouver l'absence de fuite) | Partielle : automatique sauf l'investigation |
| S3 | Crash d'un conteneur | Disponibilité | Détection par health check périodique (`POST /incidents`), restart + vérif | Oui (watcher à développer) |
| S4 | Perte de la BDD / corruption | Données | `RestoreDatabaseAction` (restauration de sauvegarde) + vérif transaction | Oui (cible ; action à développer) |
| S5 | Perte du PC Hôte | Site | Hors périmètre démontrable | Non |

Distinguer **restauration de disponibilité** (S1, S3) et **correction de compromission** (S2) : les actions sont différentes.

État d'avancement (19/10) : le pipeline couvre S1 (redémarrage + vérification) dans `services/remediation/`. Restent à développer : `WafIpBlocker`, `VaultSecretRotator` (S1/S2), le watcher de health check (S3) et `RestoreDatabaseAction` (S4, droits élevés sur la BDD à encadrer). Tant qu'ils n'existent pas, ces scénarios ne sont **pas** automatiques : le moteur déclare l'incident en échec plutôt que résolu.

## 3. Objectifs de continuité et de reprise

| Service | Criticité | RTO cible | RTO mesuré | RPO cible | RPO mesuré | Source de la mesure |
|---|---|---|---|---|---|---|
| Paiement (API + auth + BDD) | À DÉFINIR | À DÉFINIR | À MESURER | À DÉFINIR | À MESURER | Événements JSON de remédiation (Loki) |
| Dashboard | À DÉFINIR | | | | | |
| Observabilité | À DÉFINIR | | | | | |

Définition de la reprise : **API saine ET transaction de test réussie** (pas seulement un conteneur relancé).

Mesure du RTO (décision du 19/10) : **début d'attaque → `incident.resolved`**. Le début d'attaque vient du journal horodaté du script d'attaque ; la fin, de l'événement `incident.resolved` dans Loki. On décompose aussi le délai de détection (début d'attaque → `incident.detected`) et le temps de remédiation (`incident.detected` → `incident.resolved`).

## 4. Responsabilités

Pendant l'incident, **aucune intervention humaine** (Zero-Touch). Les rôles décrivent ce que l'équipe fait après (proposition à valider).

| Rôle | Qui | Responsabilité après l'incident |
|---|---|---|
| Pilotage / décision | Kevin | Relit les événements, confirme la clôture, ajuste le seuil ML |
| Infra / WAF | Hugo | Vérifie le WAF et les réseaux, exécute le script de reset d'état |
| Backend / BDD | Antoine | Contrôle l'intégrité de la BDD et la restauration |
| Front / dashboard | Gabriel | Vérifie l'affichage avant / pendant / après |
| Investigation / red team | François | Investigue S2 (fuite éventuelle), rapporte l'attaque jouée |

## 5. Choix de restauration
Stratégie de sauvegarde (fréquence, lieu, chiffrement), restauration de la BDD (via `RestoreDatabaseAction`, S4), rejouabilité (script de reset d'état). Le RPO cible découle de la fréquence de sauvegarde. À DÉFINIR avec Hugo et Antoine.

## 6. Procédures
Les procédures opérationnelles vont dans `docs/procedures/`. Une procédure par scénario.

## 7. Essais et preuves
Chaque essai : date, scénario, résultat, RTO observé, intervention humaine (oui/non), lien vers log ou capture.

| Date | Scénario | Résultat | RTO observé | Intervention humaine | Preuve |
|---|---|---|---|---|---|
| | | | | | |

Objectif : ≥ 5 passages sans intervention.

## 8. Risques qui subsistent après la reprise
À DÉFINIR. À rédiger honnêtement : ex. attaquant qui revient, secret compromis non détecté, SPOF du PC Hôte, faux positif du modèle ML.
